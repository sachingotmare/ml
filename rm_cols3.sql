SELECT column_name, ordinal_position FROM information_schema.columns
WHERE table_schema='lab_test3' AND table_name='RateMasters'
ORDER BY ordinal_position;