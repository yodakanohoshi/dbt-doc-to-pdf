with orders as (
    select * from {{ ref('stg_orders') }}
),

order_items as (
    select
        order_id,
        count(*) as item_count,
        sum(quantity) as total_quantity
    from {{ ref('stg_order_items') }}
    group by order_id
)

select
    o.order_id,
    o.customer_id,
    o.status,
    o.amount,
    o.ordered_at,
    coalesce(i.item_count, 0) as item_count,
    coalesce(i.total_quantity, 0) as total_quantity
from orders o
left join order_items i using (order_id)
