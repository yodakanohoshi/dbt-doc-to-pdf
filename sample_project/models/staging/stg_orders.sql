select
    101 as order_id, 1 as customer_id, 'completed' as status,
    3500 as amount, '2024-01-10'::date as ordered_at
union all
select 102, 1, 'completed', 1200, '2024-02-15'::date
union all
select 103, 2, 'pending',   8000, '2024-03-01'::date
union all
select 104, 3, 'completed', 500,  '2024-03-20'::date
