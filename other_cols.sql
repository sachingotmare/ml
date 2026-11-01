SELECT 'AccountMasters' AS tbl, column_name FROM information_schema.columns
WHERE table_schema='lab_test3' AND table_name='AccountMasters'
UNION ALL
SELECT 'Patients', column_name FROM information_schema.columns
WHERE table_schema='lab_test3' AND table_name='Patients'
UNION ALL
SELECT 'Doctors', column_name FROM information_schema.columns
WHERE table_schema='lab_test3' AND table_name='Doctors'
ORDER BY 1, 2;