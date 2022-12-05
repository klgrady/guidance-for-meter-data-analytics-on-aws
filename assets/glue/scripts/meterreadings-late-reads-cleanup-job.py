import sys
from awsglue.transforms import *
from awsglue.utils import getResolvedOptions
from pyspark.context import SparkContext
from awsglue.context import GlueContext
from awsglue.dynamicframe import DynamicFrame
from awsglue.job import Job


args = getResolvedOptions(sys.argv, ["JOB_NAME", "MDA_DATABASE_STAGING","MDA_DATABASE_INTEGRATED", "STAGING_TABLE_NAME", "TARGET_TABLE_NAME","INTEGRATED_BUCKET_NAME"])
sc = SparkContext()
glueContext = GlueContext(sc)
spark = glueContext.spark_session
job = Job(glueContext)
job.init(args["JOB_NAME"], args)

logger = glueContext.get_logger()

# Script generated for node Data Catalog table
DataCatalogtable_node1 = glueContext.create_dynamic_frame.from_catalog(
    database=args["MDA_DATABASE_INTEGRATED"],
    table_name=args["TARGET_TABLE_NAME"],
    transformation_ctx="DataCatalogtable_node1",
    additional_options = {'useS3ListImplementation': True},
    push_down_predicate = "(reading_type = 'crrnt' AND year = '2022' AND month = '11' AND day = '29' AND hour = '22')"
)

mappings = [
    ("meter_id", "string", "meter_id", "string"),
    ("reading_value", "string", "reading_value", "double"),
    ("reading_type", "string", "reading_type", "string"),
    ("reading_date_time", "string", "reading_date_time", "timestamp"),
    ("unit", "string", "unit", "string"),
    ("obis_code", "string", "obis_code", "string"),
    ("phase", "string", "phase", "string"),
    ("reading_source", "string", "reading_source", "string"),
    ("year", "string", "year", "int"),
    ("month", "string", "month", "int"),
    ("day", "string", "day", "int"),
    ("hour", "string", "hour", "int"),
]

# Script generated for node ApplyMapping
source_map = ApplyMapping.apply(
    frame=DataCatalogtable_node1,
    mappings=mappings,
    transformation_ctx="ApplyMapping_node2",
)

write_sink = glueContext.getSink(
    path="s3://"+args["INTEGRATED_BUCKET_NAME"]+"/readings/parquet/",
    connection_type="s3",
    updateBehavior="UPDATE_IN_DATABASE",
    partitionKeys= ["reading_type", "year", "month", "day", "hour"],
    compression="snappy",
    enableUpdateCatalog=True,
    transformation_ctx="write_context",
    options = {
        "groupFiles": "inPartition",
        "groupSize": "104857600" # 104857600 bytes (100 MB)
    }
)

write_sink.setCatalogInfo(
    catalogDatabase=args["MDA_DATABASE_INTEGRATED"], catalogTableName=args["TARGET_TABLE_NAME"]
)
write_sink.setFormat("glueparquet")
write_sink.writeFrame(source_map)

# Purge data older than 1 hour, after re-writing the partition. Any deleted data goes to purged folder in bucket
glueContext.purge_table(
    args["MDA_DATABASE_INTEGRATED"],
    args["TARGET_TABLE_NAME"],
    options = {
        "partitionPredicate": "(reading_type = 'crrnt' AND year = '2022' AND month = '11' AND day = '29' AND hour = '22')",
        "retentionPeriod": 1,
        "manifestFilePath": "s3://"+args["INTEGRATED_BUCKET_NAME"]+"/readings/purged/"
    },
    transformation_ctx="source_map"
)

job.commit()