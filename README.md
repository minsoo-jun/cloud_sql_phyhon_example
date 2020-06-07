# cloud_sql_phyhon_example

## Original Sources
https://github.com/GoogleCloudPlatform/python-docs-samples/tree/master/cloud-sql/mysql/sqlalchemy


## Packaging
```shell script
export PROJECT_ID="minsoojunprj"
export INSTANCE_CONNECTION_NAME="minsoojunprj:us-central1:inspections"
export MY_DB_USER="store-service"
export MY_DB_PASS="store-service"
export MY_DB="inspection_reports"
export SUBSCRIPTION_NAME="new-lab-report"

gcloud builds submit --tag gcr.io/$PROJECT_ID/store-service

gcloud run deploy store-service --image gcr.io/$YOUR_PROJECT_ID/store-service  --platform managed \
  --region us-central1 \
  --allow-unauthenticated --concurrency=40 --memory 1G

gcloud run services update store-service \
	--platform managed \
  	--region us-central1 \
    --add-cloudsql-instances $INSTANCE_CONNECTION_NAME \
    --set-env-vars CLOUD_SQL_CONNECTION_NAME=$INSTANCE_CONNECTION_NAME,\
DB_USER=$MY_DB_USER,DB_PASS=$MY_DB_PASS,DB_NAME=$MY_DB,SUBSCRIPTION_NAME=$SUBSCRIPTION_NAME,PROJECT_ID=$YOUR_PROJECT_ID 


#### set pub/sub
```
#create service account
gcloud iam service-accounts create pubsub-cloud-run-invoker --display-name "PubSub Cloud Run Invoker"

#新しいサービス アカウントに、store-serviceを呼び出す権限を付与
gcloud run services add-iam-policy-binding store-service --member=serviceAccount:pubsub-cloud-run-invoker@$GOOGLE_CLOUD_PROJECT.iam.gserviceaccount.com --role=roles/run.invoker --region us-central1 --platform managed

#「new-lab-report」メッセージがパブリッシュされたときに store-serviceを呼び出すよう Pub/Sub 
export PROJECT_NUMBER=$(gcloud projects list --filter="$GOOGLE_CLOUD_PROJECT" --format='value(PROJECT_NUMBER)')

gcloud projects add-iam-policy-binding $GOOGLE_CLOUD_PROJECT --member=serviceAccount:service-$PROJECT_NUMBER@gcp-sa-pubsub.iam.gserviceaccount.com --role=roles/iam.serviceAccountTokenCreator

#別の環境変数にstore-serviceの URL を設定します。
export STORE_SERVICE_URL=$(gcloud run services describe store-service --platform managed --region us-central1 --format="value(status.address.url)")
```

```
## Deploy to Cloud Run
See the Cloud Run documentation for more details on connecting a Cloud Run service to Cloud SQL.

### Build the container image:
```
gcloud builds submit --tag gcr.io/[YOUR_PROJECT_ID]/run-mysql
```
### Deploy the service to Cloud Run:
```
gcloud run deploy run-mysql --image gcr.io/[YOUR_PROJECT_ID]/run-mysql
```
Take note of the URL output at the end of the deployment process.

### Configure the service for use with Cloud Run
```
gcloud run services update run-mysql \
    --add-cloudsql-instances [INSTANCE_CONNECTION_NAME] \
    --set-env-vars CLOUD_SQL_CONNECTION_NAME=[INSTANCE_CONNECTION_NAME],\
DB_USER=[MY_DB_USER],DB_PASS=[MY_DB_PASS],DB_NAME=[MY_DB]
```
Replace environment variables with the correct values for your Cloud SQL instance configuration.

This step can be done as part of deployment but is separated for clarity.

### Navigate your browser to the URL noted in step 2.
For more details about using Cloud Run see http://cloud.run. Review other Python on Cloud Run samples.