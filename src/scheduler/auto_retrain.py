import time
import logging
from apscheduler.schedulers.background import BackgroundScheduler
from src.data.data_fetcher import CloudDataFetcher
from src.trade.config import Settings
import boto3
import io
import json

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class CloudRetrainScheduler:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.data_fetcher = CloudDataFetcher(settings)
        self.scheduler = BackgroundScheduler()
        self.s3_client = boto3.client(
            's3',
            aws_access_key_id=settings.aws_access_key_id,
            aws_secret_access_key=settings.aws_secret_access_key,
            region_name=settings.aws_region
        )
        self.bucket = settings.s3_bucket_name

    def hourly_retrain_job(self):
        logger.info("Starting hourly retraining job...")
        symbol = self.settings.default_symbol
        
        # 1. Fetch latest data and upload to S3
        logger.info(f"Fetching latest data for {symbol}...")
        try:
            file_key = self.data_fetcher.fetch_and_upload(symbol, timeframe='1h', limit=500)
            logger.info(f"Uploaded new data to S3: {file_key}")
            
            # 2. Download from S3 (simulating pulling the new historical dataset)
            df = self.data_fetcher.download_data(symbol, timeframe='1h')
            logger.info(f"Downloaded {len(df)} rows for retraining.")
            
            # 3. Simulate model retraining and evaluation
            # In a real scenario, you would train your ML model here
            # and evaluate if the new model performs better than the old one.
            new_win_rate = 0.58
            new_sharpe = 1.2
            
            if new_win_rate > self.settings.win_rate_min and new_sharpe > self.settings.validation_sharpe_min:
                logger.info("New model outperforms constraints. Serializing and uploading to S3...")
                
                # 4. Upload model weights/config to S3
                model_config = {
                    "win_rate": new_win_rate,
                    "sharpe": new_sharpe,
                    "timestamp": time.time(),
                    "weights": "simulated_new_weights"
                }
                
                buffer = io.BytesIO(json.dumps(model_config).encode('utf-8'))
                model_key = f"models/{symbol.replace('/', '_')}_latest.json"
                self.s3_client.upload_fileobj(buffer, self.bucket, model_key)
                
                logger.info(f"Successfully uploaded new model to S3: {model_key}")
            else:
                logger.info("New model did not improve. Keeping existing model.")
                
        except Exception as e:
            logger.error(f"Error during retrain job: {e}")

    def start(self):
        # Run the job every hour
        self.scheduler.add_job(self.hourly_retrain_job, 'interval', seconds=self.settings.poll_interval_seconds)
        self.scheduler.start()
        logger.info(f"Cloud Retrain Scheduler started. Polling every {self.settings.poll_interval_seconds} seconds.")

    def stop(self):
        self.scheduler.shutdown()
        logger.info("Cloud Retrain Scheduler stopped.")
