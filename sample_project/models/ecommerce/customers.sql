with raw_customers as (
    select * from {{ ref('stg_customers') }}
),

orders as (
    select
        customer_id,
        count(*) as order_count,
        sum(amount) as lifetime_value,
        min(ordered_at) as first_order_at,
        max(ordered_at) as latest_order_at
    from {{ ref('stg_orders') }}
    group by customer_id
)

select
    c.customer_id,
    c.first_name,
    c.last_name,
    c.email,
    c.created_at,
    coalesce(o.order_count, 0) as order_count,
    coalesce(o.lifetime_value, 0) as lifetime_value,
    o.first_order_at,
    o.latest_order_at
from raw_customers c
left join orders o using (customer_id)
