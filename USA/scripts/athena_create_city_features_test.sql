-- City Features test table (India + USA CSVs flat in same folder, same columns)

CREATE EXTERNAL TABLE two_tower_shabbir.city_features (
    pincode STRING,
    state_original STRING,
    major_city STRING,
    latitude DOUBLE,
    longitude DOUBLE,
    region STRING,
    coastal_city STRING,
    distance_to_state_capital DOUBLE,
    city_tier STRING,
    is_metro_city STRING,
    is_smart_city STRING,
    is_state_capital STRING,
    is_union_territory_capital STRING,
    literacy_rate DOUBLE,
    median_age_estimate DOUBLE,
    consumer_price_index DOUBLE,
    income_bucket STRING,
    has_airport STRING,
    has_international_airport STRING,
    has_metro_rail STRING,
    has_seaport STRING,
    major_railway_station STRING,
    internet_penetration_state DOUBLE,
    smartphone_penetration_state DOUBLE,
    digital_payment_index DOUBLE,
    is_it_hub STRING,
    is_manufacturing_hub STRING,
    is_financial_center STRING,
    is_textile_hub STRING,
    is_education_hub STRING,
    is_tourist_city STRING,
    is_coastal STRING,
    district_population_numeric BIGINT,
    district_population STRING,
    sex_ratio DOUBLE
)
ROW FORMAT DELIMITED
FIELDS TERMINATED BY ','
STORED AS INPUTFORMAT 'org.apache.hadoop.mapred.TextInputFormat'
OUTPUTFORMAT 'org.apache.hadoop.hive.ql.io.HiveIgnoreKeyTextOutputFormat'
LOCATION 's3://mobavenue-simplismart-aws-s3-apse-sg/rtb/data/ml/Temp_Test_Folder/City_Features/'
TBLPROPERTIES ('skip.header.line.count'='1');

-- Upload both CSVs flat into:
--   s3://mobavenue-simplismart-aws-s3-apse-sg/rtb/data/ml/Temp_Test_Folder/City_Features/
--
-- Test:
--   SELECT COUNT(*) FROM two_tower_shabbir.city_features;
--   SELECT * FROM two_tower_shabbir.city_features LIMIT 10;
