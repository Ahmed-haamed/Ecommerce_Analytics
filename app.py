"""Interactive dashboard. Start with streamlit run app.py."""
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from analysis import load_data, summary, breakdown

st.set_page_config(page_title='Commerce | Performance Review', page_icon='📊', layout='wide')
px.defaults.template = 'plotly_white'
px.defaults.color_discrete_sequence = ['#087f8c', '#e59b43', '#546a7b', '#b45b69', '#869d7a']


@st.cache_data
def get_data():
    return load_data()


_, orders, items, _, _ = get_data()
st.title('Commerce performance review')
st.caption('Customer, order and product intelligence · EGP · January–September 2026')
st.sidebar.header('Explore your business')
dates = st.sidebar.date_input('Order date range', (orders.Order_Date.min().date(), orders.Order_Date.max().date()),
    min_value=orders.Order_Date.min().date(), max_value=orders.Order_Date.max().date())
scope = orders.copy()
if len(dates) == 2:
    scope = scope.loc[scope.Order_Date.between(pd.Timestamp(dates[0]), pd.Timestamp(dates[1]))]
else:
    st.info('Select both a start date and an end date.')
    st.stop()
for column, label in [('Sales_Channel', 'Sales channel'), ('City', 'City'), ('Customer_Segment', 'Customer segment')]:
    values = sorted(orders[column].unique())
    selected = st.sidebar.multiselect(label, values, default=values)
    scope = scope.loc[scope[column].isin(selected)]
statuses = st.sidebar.multiselect('Commercial view · order status', sorted(orders.Order_Status.unique()), default=['Delivered'])
selected_orders = scope.loc[scope.Order_Status.isin(statuses)]
selected_items = items.loc[items.Order_ID.isin(selected_orders.Order_ID)]
st.sidebar.caption('Filters update KPIs and charts. Operational status charts use all statuses within the selected dates, channels, cities and segments.')
overview, products, operations = st.tabs(['Overview', 'Products & customers', 'Operations'])


def chart(fig, height=360):
    fig.update_layout(margin=dict(l=12, r=12, t=50, b=25), height=height)
    st.plotly_chart(fig, width='stretch', config={'displaylogo': False})


with overview:
    if selected_orders.empty:
        st.info('No orders match these filters. Change the selections in the sidebar.')
    else:
        kpi = summary(selected_orders)
        values = [('Orders', f"{kpi['orders']:,}"), ('Merchandise sales', f"EGP {kpi['sales']:,.0f}"),
                  ('Product profit', f"EGP {kpi['profit']:,.0f}"),
                  ('Product margin', f"{kpi['margin']:.1%}" if kpi['margin'] is not None else 'N/A'),
                  ('Average order value', f"EGP {kpi['aov']:,.0f}" if kpi['aov'] is not None else 'N/A')]
        for column, (label, value) in zip(st.columns(5), values):
            column.metric(label, value)
        st.caption(f"Financial coverage {kpi['financial_orders']:,}/{kpi['orders']:,} orders. Sales, profit and AOV use complete validated orders. Product profit excludes shipping, refunds, marketing and overhead.")
        if any(status != 'Delivered' for status in statuses):
            st.warning('This view includes non-delivered order values. Treat these as recorded merchandise values, not realized revenue.')
        st.info('September ends on 27 September. Compare complete months separately. Status reflects the supplied extract and may change later.')
        monthly = breakdown(selected_orders, 'Month')
        chart(px.line(monthly, x='Month', y='Sales_EGP', markers=True, title='Merchandise sales by order month', labels={'Sales_EGP': 'Sales (EGP)'}))
        chart(px.bar(monthly, x='Month', y='Orders', title='Order volume by month'))
        with st.container(border=True):
            st.subheader('What changed between two months?')
            st.caption('Compare complete calendar months. Each step shows a category contribution to the sales change.')
            coverage_start = max(pd.Timestamp(dates[0]), orders.Order_Date.min())
            coverage_end = min(pd.Timestamp(dates[1]), orders.Order_Date.max())
            complete_months = [str(month) for month in pd.period_range(coverage_start, coverage_end, freq='M')
                               if month.start_time >= coverage_start and month.end_time.normalize() <= coverage_end]
            if len(complete_months) < 2 or selected_items.empty:
                st.info('Select a date range covering at least two complete months with validated product data to compare sales.')
            else:
                start_column, end_column = st.columns(2)
                start_month = start_column.selectbox('Starting month', complete_months[:-1], index=len(complete_months)-2)
                later_months = [month for month in complete_months if month > start_month]
                end_month = end_column.selectbox('Ending month', later_months, index=len(later_months)-1)
                category_months = selected_items.groupby(['Category', 'Month']).Line_Sales_EGP.sum().unstack(fill_value=0)
                category_months = category_months.reindex(columns=complete_months, fill_value=0)
                change = (category_months[end_month] - category_months[start_month]).sort_values()
                starting_sales = category_months[start_month].sum()
                ending_sales = category_months[end_month].sum()
                change_percent = f'{ending_sales / starting_sales - 1:+.1%}' if starting_sales else 'N/A · starting sales are zero'
                st.metric('Change in merchandise sales', f'EGP {ending_sales - starting_sales:+,.2f}', change_percent)
                bridge = go.Figure(go.Waterfall(
                    x=[start_month, *change.index, end_month],
                    measure=['absolute', *(['relative'] * len(change)), 'total'],
                    y=[starting_sales, *change.values, 0],
                    text=[f'{starting_sales:,.0f}', *[f'{value:+,.0f}' for value in change], f'{ending_sales:,.0f}'],
                    textposition='outside',
                    customdata=[starting_sales, *change.values, ending_sales],
                    hovertemplate='<b>%{x}</b><br>Sales / change · EGP %{customdata:,.2f}<extra></extra>',
                    increasing={'marker': {'color': '#35a98b'}}, decreasing={'marker': {'color': '#c96378'}},
                    totals={'marker': {'color': '#087f8c'}}, connector={'line': {'color': '#bac9cf', 'width': 1}}))
                bridge.update_layout(template='plotly_white', showlegend=False, yaxis_title='Merchandise sales (EGP)')
                bridge.update_xaxes(type='category', tickangle=-20, automargin=True)
                bridge.update_yaxes(rangemode='tozero')
                chart(bridge, height=490)
                st.caption('All sidebar filters apply. Categories with no sales in a compared month contribute zero for that month. The chart describes the change; its underlying causes require investigation.')
        left, right = st.columns(2)
        with left:
            chart(px.bar(breakdown(selected_orders, 'Sales_Channel'), x='Sales_Channel', y='Sales_EGP', title='Sales by channel', labels={'Sales_EGP': 'Sales (EGP)', 'Sales_Channel': ''}))
        with right:
            chart(px.bar(breakdown(selected_orders, 'City'), x='City', y='Sales_EGP', title='Sales by customer city', labels={'Sales_EGP': 'Sales (EGP)'}))

with products:
    if selected_items.empty:
        st.info('No validated product lines match the current filters.')
    else:
        categories = st.multiselect('Product detail category filter', sorted(selected_items.Category.unique()), default=sorted(selected_items.Category.unique()))
        detail = selected_items.loc[selected_items.Category.isin(categories)].groupby(['Category', 'Product'], as_index=False).agg(
            Line_Sales_EGP=('Line_Sales_EGP', 'sum'), Line_Profit_EGP=('Line_Profit_EGP', 'sum'), Units=('Quantity', 'sum'))
        st.caption('The category selector applies to the product charts and table below. Sidebar filters apply throughout this commercial view.')
        if detail.empty:
            st.info('Select at least one category to explore product performance.')
        else:
            detail['Margin'] = detail.Line_Profit_EGP / detail.Line_Sales_EGP
            category_colors = dict(zip(sorted(items.Category.unique()),
                ['#c96378', '#8a79cd', '#35a98b', '#249db9', '#638dc8', '#d9a047']))
            category = detail.groupby('Category').Line_Sales_EGP.sum().sort_values(ascending=False)
            with st.container(border=True):
                st.subheader('Which categories and products drive sales?')
                st.caption('Inner ring shows categories; outer ring shows products. Click a category to explore it and click the center to return. Sector area represents sales.')
                sales_mix = px.sunburst(detail, path=[px.Constant('Sales (EGP)'), 'Category', 'Product'],
                    values='Line_Sales_EGP', color='Category', color_discrete_map=category_colors)
                sales_mix.update_traces(textinfo='label', insidetextorientation='auto',
                    marker=dict(line=dict(width=2, color='white')),
                    hovertemplate='<b>%{label}</b><br>Sales · EGP %{value:,.2f}<br>Share of parent · %{percentParent:.1%}<extra></extra>')
                sales_mix.data[0].marker.colors = ['#e6eef0' if label == 'Sales (EGP)' else color
                    for label, color in zip(sales_mix.data[0].labels, sales_mix.data[0].marker.colors)]
                chart(sales_mix, height=540)
                leaders = category.head(2)
                st.caption(f"{' + '.join(leaders.index)} account for {leaders.sum() / category.sum():.1%} of sales in the selected categories. Total merchandise sales are EGP {category.sum():,.2f}.")
            with st.container(border=True):
                st.subheader('Which products combine sales and margin?')
                st.caption('Each bubble is a product. Bubble area represents units sold and color represents category. Hover for exact values.')
                product_bubbles = px.scatter(detail, x='Line_Sales_EGP', y='Margin', size='Units',
                    color='Category', color_discrete_map=category_colors, size_max=28,
                    hover_name='Product', hover_data={'Line_Sales_EGP': ':,.2f', 'Line_Profit_EGP': ':,.2f', 'Margin': ':.2%', 'Units': True},
                    labels={'Line_Sales_EGP': 'Merchandise sales (EGP)', 'Line_Profit_EGP': 'Product profit (EGP)', 'Margin': 'Product profit margin', 'Units': 'Units sold'})
                product_bubbles.update_traces(marker=dict(opacity=.8, line=dict(width=1, color='white')))
                weighted_margin = detail.Line_Profit_EGP.sum() / detail.Line_Sales_EGP.sum()
                product_bubbles.add_hline(y=weighted_margin, line_dash='dot', line_color='#8397a2')
                product_bubbles.update_yaxes(tickformat='.0%', automargin=True)
                product_bubbles.update_xaxes(rangemode='tozero', tickformat='~s')
                product_bubbles.update_layout(legend=dict(orientation='h', y=-.22, x=0, title=None))
                chart(product_bubbles, height=520)
                st.caption(f'Dotted line = weighted product margin for this selection ({weighted_margin:.2%}). Product profit excludes shipping, refunds, marketing and overhead.')
            chart(px.bar(detail.sort_values('Line_Profit_EGP').tail(10), x='Line_Profit_EGP', y='Product', orientation='h', title='Top products by profit · selected categories', labels={'Line_Profit_EGP': 'Product profit (EGP)'}))
            st.dataframe(detail, hide_index=True, width='stretch')
    if not selected_orders.empty:
        segments = breakdown(selected_orders, 'Customer_Segment')
        segments['Observed_repeat_rate'] = segments.Customer_Segment.map({key: summary(group)['repeat_rate'] for key, group in selected_orders.groupby('Customer_Segment')})
        chart(px.bar(segments, x='Customer_Segment', y='AOV_EGP', title='Order value by supplied customer segment', labels={'AOV_EGP': 'AOV (EGP)', 'Customer_Segment': ''}))
        st.dataframe(segments, hide_index=True, width='stretch')
        st.caption('Observed repeat rate means 2+ orders per customer in the selected window and statuses. Supplied segment labels may differ from observed behavior. This is not a retention or lifetime-value measure.')
        st.subheader('Payment comparison')
        st.dataframe(breakdown(selected_orders, 'Payment_Method'), hide_index=True, width='stretch')

with operations:
    st.caption('All statuses within the sidebar date and customer/channel scope. Commercial status selection does not alter this tab.')
    if scope.empty:
        st.info('No orders match the operational scope.')
    else:
        dimension_labels = {'Sales_Channel': 'Sales channel', 'Customer_Segment': 'Customer segment'}
        dimension = st.radio('Compare operations by', list(dimension_labels),
                             format_func=dimension_labels.get, horizontal=True)
        status = scope.groupby([dimension, 'Order_Status']).size().reset_index(name='Orders')
        status['Share'] = status.Orders / status.groupby(dimension).Orders.transform('sum')
        chart(px.bar(status, x=dimension, y='Share', color='Order_Status', title='Order status mix',
            hover_data=['Orders'], labels={dimension: dimension_labels[dimension], 'Order_Status': 'Order status', 'Share': 'Share of orders'},
            color_discrete_map={'Delivered': '#087f8c', 'Processing': '#e59b43', 'Returned': '#7462a3', 'Cancelled': '#b45b69'}).update_yaxes(tickformat='.0%'))
        valid_days = scope.loc[scope.Delivery_Days.notna()]
        st.subheader('Delivery experience')
        st.caption(f"Delivery coverage {len(valid_days):,}/{scope.Order_Status.eq('Delivered').sum():,} delivered orders. There is no promised delivery SLA in the source.")
        if valid_days.empty:
            st.info('No delivered orders with valid delivery dates match this scope. Adjust the filters to explore delivery times.')
        else:
            delivery_mix = valid_days.groupby([dimension, 'Delivery_Days']).size().reset_index(name='Orders')
            delivery_mix['Delivery_time'] = delivery_mix.Delivery_Days.map(
                lambda days: f'{days:g} day' if days == 1 else f'{days:g} days')
            delivery_mix['Group_share'] = delivery_mix.Orders / delivery_mix.groupby(dimension).Orders.transform('sum')
            colors = dict(zip(sorted(orders[dimension].unique()), px.defaults.color_discrete_sequence))
            labels = {dimension: dimension_labels[dimension], 'Delivery_Days': 'Delivery time (days)',
                      'Orders': 'Delivered orders', 'Group_share': 'Share within group'}
            mix_tab, volume_tab = st.tabs(['Explore the mix', 'Compare delivery times'])
            with mix_tab.container(border=True):
                st.subheader('Delivery mix')
                st.caption('Click a group to explore its delivery times. Click the center to return. Sector size represents orders.')
                mix_chart = px.sunburst(delivery_mix,
                    path=[px.Constant('Delivered orders'), dimension, 'Delivery_time'],
                    values='Orders', color=dimension, color_discrete_map=colors)
                mix_chart.update_traces(textinfo='label', insidetextorientation='auto',
                    marker=dict(line=dict(width=2, color='white')),
                    hovertemplate='<b>%{label}</b><br>Delivered orders · %{value:,.0f}<br>Share of parent group · %{percentParent:.1%}<extra></extra>')
                mix_chart.data[0].marker.colors = [
                    '#e6eef0' if label == 'Delivered orders' else color
                    for label, color in zip(mix_chart.data[0].labels, mix_chart.data[0].marker.colors)]
                chart(mix_chart, height=470)
            with volume_tab.container(border=True):
                st.subheader('Delivery time and order volume')
                st.caption('Larger bubbles mean more orders. Hover to see the order count and share within each group.')
                volume_chart = px.scatter(delivery_mix, x='Delivery_Days', y=dimension,
                    size='Orders', color=dimension, size_max=20, color_discrete_map=colors,
                    custom_data=[dimension, 'Orders', 'Group_share'], labels=labels)
                volume_chart.update_traces(marker=dict(opacity=.85, line=dict(width=1.5, color='white')),
                    hovertemplate='<b>%{customdata[0]}</b><br>Delivery time · %{x:g} days<br>Delivered orders · %{customdata[1]:,.0f}<br>Share within group · %{customdata[2]:.1%}<extra></extra>')
                volume_chart.update_layout(showlegend=False)
                volume_chart.update_xaxes(dtick=1, range=[max(0, delivery_mix.Delivery_Days.min() - 1),
                                                        delivery_mix.Delivery_Days.max() + 1],
                                         gridcolor='#e4ecef', zeroline=False)
                volume_chart.update_yaxes(title=None, categoryorder='array',
                    categoryarray=sorted(delivery_mix[dimension].unique(), reverse=True),
                    gridcolor='#e4ecef', automargin=True)
                chart(volume_chart, height=470)
            st.caption(f'Average delivery time in this scope is {valid_days.Delivery_Days.mean():.2f} days. Both charts count each delivered order once and use orders with valid delivery dates.')
        st.metric('Recorded shipping fees · all statuses in scope', f'EGP {scope.Shipping_Fee_EGP.sum():,.2f}')
        st.caption(f'{scope.Shipping_Fee_EGP.isna().sum()} orders have unknown shipping fees. Fees are summed once per order and are separate from product profit.')

