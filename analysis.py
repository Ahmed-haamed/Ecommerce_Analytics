"""Reproducible data validation and analysis. Run python analysis.py."""
from pathlib import Path
import json
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent
RAW = ROOT / 'data' / 'raw'
OUT = ROOT / 'outputs'


def load_data():
    tables = {name: pd.read_csv(RAW / f'{name}_raw.csv')
              for name in ['customers', 'orders', 'order_items']}
    audit = {name: {'raw_rows': len(frame), 'exact_duplicates': int(frame.duplicated().sum()),
                    'missing': frame.isna().sum().to_dict(),
                    'dtypes': frame.dtypes.astype(str).to_dict()}
             for name, frame in tables.items()}
    duplicate_sales = tables['order_items'].loc[tables['order_items'].duplicated(), 'Line_Sales_EGP'].sum()
    customers, orders, items = [tables[name].drop_duplicates().copy() for name in tables]
    for frame, key in [(customers, 'Customer_ID'), (orders, 'Order_ID')]:
        if frame[key].isna().any() or frame[key].duplicated().any():
            raise ValueError(f'Invalid or conflicting primary key {key}')
    if not orders.Customer_ID.isin(customers.Customer_ID).all():
        raise ValueError('Orders reference missing customers')
    if not items.Order_ID.isin(orders.Order_ID).all():
        raise ValueError('Items reference missing orders')
    for frame, columns in [(customers, ['Signup_Date']), (orders, ['Order_Date', 'Delivery_Date'])]:
        for column in columns:
            frame[column] = pd.to_datetime(frame[column], errors='coerce')
    if orders.Order_Date.isna().any():
        raise ValueError('Invalid order dates require review')
    customers[['City', 'Customer_Segment']] = customers[['City', 'Customer_Segment']].fillna('Unknown')
    orders['Payment_Method'] = orders.Payment_Method.fillna('Unknown')
    numeric = items.select_dtypes(include='number')
    invalid = (~np.isfinite(numeric).all(axis=1) | (items.Quantity <= 0)
               | (items.Quantity % 1 != 0) | (items.Unit_Price_EGP <= 0)
               | (items.Unit_Cost_EGP < 0) | ~items.Discount_Rate.between(0, 1))
    sales = items.Quantity * items.Unit_Price_EGP * (1 - items.Discount_Rate)
    cost = items.Quantity * items.Unit_Cost_EGP
    mismatch = ((sales - items.Line_Sales_EGP).abs() > .02) | ((cost - items.Line_Cost_EGP).abs() > .02) | ((items.Line_Sales_EGP - items.Line_Cost_EGP - items.Line_Profit_EGP).abs() > .02)
    quarantined = items.loc[invalid | mismatch].copy()
    quarantined['Reason'] = np.where(invalid.loc[quarantined.index], 'Invalid numeric input', 'Line arithmetic mismatch')
    affected = quarantined.Order_ID.unique()
    valid = items.loc[~(invalid | mismatch)].copy()
    totals = valid.groupby('Order_ID').agg(Sales_EGP=('Line_Sales_EGP', 'sum'),
        Profit_EGP=('Line_Profit_EGP', 'sum'), Units=('Quantity', 'sum'))
    orders = orders.merge(totals, on='Order_ID', how='left', validate='one_to_one')
    orders['Finance_Eligible'] = ~orders.Order_ID.isin(affected) & orders.Sales_EGP.notna()
    orders.loc[~orders.Finance_Eligible, ['Sales_EGP', 'Profit_EGP', 'Units']] = np.nan
    orders = orders.merge(customers, on='Customer_ID', how='left', validate='many_to_one')
    days = (orders.Delivery_Date - orders.Order_Date).dt.days
    orders['Delivery_Days'] = days.where((days >= 0) & orders.Order_Status.eq('Delivered'))
    orders['Month'] = orders.Order_Date.dt.to_period('M').astype(str)
    valid = valid.loc[~valid.Order_ID.isin(affected)].copy()
    valid = valid.merge(orders[['Order_ID', 'Order_Status', 'Month']], on='Order_ID', validate='many_to_one')
    assert np.isclose(valid.Line_Sales_EGP.sum(), orders.Sales_EGP.sum())
    assert len(orders) == tables['orders'].Order_ID.nunique()
    audit.update(duplicate_item_sales_EGP=float(duplicate_sales), quarantined_lines=len(quarantined),
        finance_excluded_orders=int((~orders.Finance_Eligible).sum()),
        delivered_missing_valid_days=int((orders.Order_Status.eq('Delivered') & orders.Delivery_Days.isna()).sum()),
        signup_after_order=int((orders.Signup_Date > orders.Order_Date).sum()),
        negative_delivery_intervals=int((days < 0).sum()),
        orphan_customer_ids=0, orphan_order_ids=0)
    return customers, orders, valid, quarantined, audit


def summary(frame):
    eligible = frame.loc[frame.Finance_Eligible]
    sales = eligible.Sales_EGP.sum()
    profit = eligible.Profit_EGP.sum()
    frequency = frame.groupby('Customer_ID').Order_ID.nunique()
    return dict(orders=len(frame), financial_orders=len(eligible), customers=frame.Customer_ID.nunique(),
                sales=float(sales), profit=float(profit), margin=float(profit / sales) if sales else None,
                aov=float(sales / len(eligible)) if len(eligible) else None,
                repeat_rate=float(frequency.ge(2).mean()) if len(frequency) else None,
                delivery_days=float(frame.Delivery_Days.mean()) if frame.Delivery_Days.notna().any() else None)


def breakdown(frame, dimension):
    result = frame.groupby(dimension, dropna=False).agg(Orders=('Order_ID', 'size'),
        Financial_Orders=('Finance_Eligible', 'sum'), Sales_EGP=('Sales_EGP', 'sum'),
        Profit_EGP=('Profit_EGP', 'sum'), Customers=('Customer_ID', 'nunique'),
        Delivery_Days=('Delivery_Days', 'mean'))
    result['Margin'] = result.Profit_EGP.div(result.Sales_EGP.replace(0, np.nan))
    result['AOV_EGP'] = result.Sales_EGP.div(result.Financial_Orders.replace(0, np.nan))
    return result.reset_index()


def run():
    OUT.mkdir(exist_ok=True)
    customers, orders, items, quarantine, audit = load_data()
    delivered = orders.loc[orders.Order_Status.eq('Delivered')]
    product_lines = items.loc[items.Order_Status.eq('Delivered')]
    for name, frame in [('clean_customers', customers), ('clean_orders', orders),
                        ('validated_items', items), ('quarantine', quarantine)]:
        frame.to_csv(OUT / f'{name}.csv', index=False)
    results = {'all_orders': summary(orders), 'delivered': summary(delivered), 'audit': audit}
    for dimension in ['Month', 'City', 'Customer_Segment', 'Sales_Channel', 'Payment_Method']:
        frame = breakdown(delivered, dimension)
        frame.to_csv(OUT / f'by_{dimension.lower()}.csv', index=False)
        results[dimension] = json.loads(frame.to_json(orient='records'))
    for dimension in ['Category', 'Product']:
        frame = product_lines.groupby(dimension).agg(Sales_EGP=('Line_Sales_EGP', 'sum'),
            Profit_EGP=('Line_Profit_EGP', 'sum')).sort_values('Sales_EGP', ascending=False).reset_index()
        frame['Margin'] = frame.Profit_EGP / frame.Sales_EGP
        frame.to_csv(OUT / f'by_{dimension.lower()}.csv', index=False)
        results[dimension] = frame.to_dict('records')
    results['status'] = orders.Order_Status.value_counts().to_dict()
    results['channel_status'] = pd.crosstab(orders.Sales_Channel, orders.Order_Status).to_dict('index')
    results['segment_repeat'] = {str(key): summary(group)['repeat_rate'] for key, group in delivered.groupby('Customer_Segment')}
    (OUT / 'results.json').write_text(json.dumps(results, indent=2, allow_nan=False), encoding='utf-8')
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import seaborn as sns
    sns.set_theme(style='whitegrid', palette=['#087f8c', '#e59b43'])
    for dimension, value in [('Month', 'Sales_EGP'), ('Category', 'Profit_EGP'), ('Sales_Channel', 'AOV_EGP'), ('Customer_Segment', 'Sales_EGP')]:
        frame = pd.DataFrame(results[dimension])
        fig, ax = plt.subplots(figsize=(9, 4.5))
        sns.barplot(data=frame, x=dimension, y=value, ax=ax, color='#087f8c')
        ax.set(title=f'Delivered orders | {value.replace("_", " ")}', xlabel='', ylabel='EGP')
        ax.tick_params(axis='x', rotation=20)
        fig.tight_layout()
        fig.savefig(OUT / f'chart_{dimension.lower()}.png', dpi=170)
        plt.close(fig)
    print(json.dumps(results, indent=2))


if __name__ == '__main__':
    run()
