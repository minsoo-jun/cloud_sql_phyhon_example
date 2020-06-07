# Copyright 2018 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import base64
import os

from flask import Flask, request
import sqlalchemy

app = Flask(__name__)

### Cloud SQL Part ############################################################
# Remember - storing secrets in plaintext is potentially unsafe. Consider using
# something like https://cloud.google.com/kms/ to help keep secrets secret.
db_user = os.environ.get("DB_USER")
db_pass = os.environ.get("DB_PASS")
db_name = os.environ.get("DB_NAME")
cloud_sql_connection_name = os.environ.get("CLOUD_SQL_CONNECTION_NAME")

def init_connection_engine():
    print('init_connection_engine')
    db_config = {
        # [START cloud_sql_mysql_sqlalchemy_limit]
        # Pool size is the maximum number of permanent connections to keep.
        "pool_size": 5,
        # Temporarily exceeds the set pool_size if no connections are available.
        "max_overflow": 2,
        # The total number of concurrent connections for your application will be
        # a total of pool_size and max_overflow.
        # [END cloud_sql_mysql_sqlalchemy_limit]
        # [START cloud_sql_mysql_sqlalchemy_backoff]
        # SQLAlchemy automatically uses delays between failed connection attempts,
        # but provides no arguments for configuration.
        # [END cloud_sql_mysql_sqlalchemy_backoff]
        # [START cloud_sql_mysql_sqlalchemy_timeout]
        # 'pool_timeout' is the maximum number of seconds to wait when retrieving a
        # new connection from the pool. After the specified amount of time, an
        # exception will be thrown.
        "pool_timeout": 30,  # 30 seconds
        # [END cloud_sql_mysql_sqlalchemy_timeout]
        # [START cloud_sql_mysql_sqlalchemy_lifetime]
        # 'pool_recycle' is the maximum number of seconds a connection can persist.
        # Connections that live longer than the specified amount of time will be
        # reestablished
        "pool_recycle": 1800,  # 30 minutes
        # [END cloud_sql_mysql_sqlalchemy_lifetime]
    }

    if os.environ.get("DB_HOST"):
        return init_tcp_connection_engine(db_config)
    else:
        return init_unix_connection_engine(db_config)

def init_tcp_connection_engine(db_config):
    print('init_tcp_connection_engine')
    # [START cloud_sql_mysql_sqlalchemy_create_tcp]
    db_socket_addr = os.environ.get("DB_HOST").split(":")

    # Extract host and port from socket address
    db_host = db_socket_addr[0]
    db_port = int(db_socket_addr[1])

    return sqlalchemy.create_engine(
        # Equivalent URL:
        # mysql+pymysql://<db_user>:<db_pass>@<db_host>:<db_port>/<db_name>
        sqlalchemy.engine.url.URL(
            drivername="mysql+pymysql",
            username=db_user,
            password=db_pass,
            host=db_host,
            port=db_port,
            database=db_name,
        ),
        # ... Specify additional properties here.
        # [START_EXCLUDE]
        **db_config
        # [END_EXCLUDE]
    )
    # [END cloud_sql_mysql_sqlalchemy_create_tcp]

def init_unix_connection_engine(db_config):
    print('init_unix_connection_engine')
    # [START cloud_sql_mysql_sqlalchemy_create_socket]
    if os.environ.get("DB_SOCKET_PATH"):
        socket_path = os.environ.get("DB_SOCKET_PATH")
    else:
        socket_path = "/cloudsql"

    return sqlalchemy.create_engine(
        # Equivalent URL:
        # mysql+pymysql://<db_user>:<db_pass>@/<db_name>?unix_socket=<socket_path>/<cloud_sql_instance_name>
        sqlalchemy.engine.url.URL(
            drivername="mysql+pymysql",
            username=db_user,
            password=db_pass,
            database=db_name,
            query={
                "unix_socket": "{}/{}".format(
                    socket_path,
                    cloud_sql_connection_name)
            }
        ),
        # ... Specify additional properties here.
        # [START_EXCLUDE]
        **db_config
        # [END_EXCLUDE]
    )
    # [END cloud_sql_mysql_sqlalchemy_create_socket]

# The SQLAlchemy engine will help manage interactions, including automatically
# managing a pool of connections to your database
db = init_connection_engine()

@app.before_first_request
def create_tables():
    print('create_tables')
    # Create tables (if they don't already exist)
    with db.connect() as conn:
        conn.execute(
            "DROP TABLE  report ;  "
        )
        conn.execute(
            "CREATE TABLE IF NOT EXISTS report ( "
            "pk MEDIUMINT NOT NULL AUTO_INCREMENT, "
            "id VARCHAR(20) NOT NULL, "
            "result TEXT, report_date timestamp NOT NULL , "
            "PRIMARY KEY (pk) "
            "); "
        )

def save_vote(report_id, report_result):
    print('save_vote')

    # [START cloud_sql_mysql_sqlalchemy_connection]
    # Preparing a statement before hand can help protect against injections.
    stmt = sqlalchemy.text(
        "INSERT INTO report ( id, result)" " VALUES ( :report_id, :report_result )"
    )
    try:
        # Using a with statement ensures that the connection is always released
        # back into the pool at the end of statement (even if an error occurs)
        with db.connect() as conn:
            conn.execute(stmt, time_cast=time_cast, report_id=report_id, report_result=report_result)
    except Exception as e:
        # If something goes wrong, handle the error in this section. This might
        # involve retrying or adjusting parameters depending on the situation.
        # [START_EXCLUDE]
        return Response(
            status=500,
            response="Unable to successfully insert inspect report ! Please check the "
                     "application logs for more details.",
        )
        # [END_EXCLUDE]
    # [END cloud_sql_mysql_sqlalchemy_connection]

    return Response(
        status=200,
        response="inspect report successfully cast for '{}' at time {}!".format(report_id, time_cast),
    )

# [START run_pubsub_handler]
@app.route('/', methods=['POST'])
def index():
    envelope = request.get_json()
    if not envelope:
        msg = 'no Pub/Sub message received'
        print('error: {msg}')
        return 'Bad Request: {msg}', 400

    if not isinstance(envelope, dict) or 'message' not in envelope:
        msg = 'invalid Pub/Sub message format'
        print('error: {msg}')
        return 'Bad Request: {msg}', 400

    pubsub_message = envelope['message']
    print(pubsub_message)
    report_id = 'World'
    report_result = 'Success'
    if isinstance(pubsub_message, dict) and 'data' in pubsub_message:
        report_id = base64.b64decode(pubsub_message['data']).decode('utf-8').strip()

    print('Hello :' + report_id)

    # [START cloud_sql_mysql_sqlalchemy_connection]
    # Preparing a statement before hand can help protect against injections.
    stmt = sqlalchemy.text(
        "INSERT INTO report ( id, result)" " VALUES ( :report_id, :report_result )"
    )
    try:
        # Using a with statement ensures that the connection is always released
        # back into the pool at the end of statement (even if an error occurs)
        with db.connect() as conn:
            conn.execute(stmt, report_id=report_id, report_result=report_result)
    except Exception as e:
        # If something goes wrong, handle the error in this section. This might
        # involve retrying or adjusting parameters depending on the situation.
        # [START_EXCLUDE]
        return ('Unable to successfully insert inspect report ! Please check the application logs for more details.', 500)
#        return Response(
#            status=500,
#            response="Unable to successfully insert inspect report ! Please check the "
#                     "application logs for more details.",
#        )
        # [END_EXCLUDE]
    # [END cloud_sql_mysql_sqlalchemy_connection]

#    return Response(
#        status=204,
#        response="inspect report successfully cast for '{}' at time {}!".format(report_id, time_cast),
#    )
    return ('inspect report successfully', 204)
# [END run_pubsub_handler]


if __name__ == '__main__':
    PORT = int(os.getenv('PORT')) if os.getenv('PORT') else 8080

    # This is used when running locally. Gunicorn is used to run the
    # application on Cloud Run. See entrypoint in Dockerfile.
    app.run(host='127.0.0.1', port=PORT, debug=True)

