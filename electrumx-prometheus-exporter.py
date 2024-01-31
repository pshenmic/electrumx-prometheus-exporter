from flask import Flask, Response
import asyncio
import requests
import json
import os
from aiorpcx import timeout_after, connect_rs

from prometheus_client import start_http_server, Counter, generate_latest, Gauge, REGISTRY, PROCESS_COLLECTOR, PLATFORM_COLLECTOR, GC_COLLECTOR
timeout = 30

bind_host = os.getenv('HOST') or None
bind_port = os.getenv('PORT') or 8003
rpc_host = os.getenv('RPC_HOST') or '127.0.0.1'
rpc_port = os.getenv('RPC_PORT') or 8000
insight_url = os.getenv('INSIGHT_URL') or None
app = Flask(__name__)

REGISTRY.unregister(PROCESS_COLLECTOR)
REGISTRY.unregister(PLATFORM_COLLECTOR)
REGISTRY.unregister(GC_COLLECTOR)

ELECTRUMX_DAEMON_HEIGHT = Gauge('electrumx_daemon_height', 'Daemon height')
ELECTRUMX_EXTERNAL_HEIGHT = Gauge('electrumx_external_height', 'External height')
ELECTRUMX_DB_HEIGHT = Gauge('electrumx_db_height', 'DB height')
ELECTRUMX_DB_FLUSH_COUNT = Gauge('electrumx_db_flush_count', 'DB flush count')

ELECTRUMX_PEERS_BAD = Gauge('electrumx_peers_bad', 'Bad peers')
ELECTRUMX_PEERS_GOOD = Gauge('electrumx_peers_good', 'Good peers')
ELECTRUMX_PEERS_NEVER = Gauge('electrumx_peers_never', 'Never peers')
ELECTRUMX_PEERS_STALE = Gauge('electrumx_peers_stale', 'Stale peers')
ELECTRUMX_PEERS_TOTAL = Gauge('electrumx_peers_total', 'Total peers')

ELECTRUMX_REQUESTS_TOTAL = Gauge('electrumx_requests_total', 'Total requests')

ELECTRUMX_SESSIONS_COUNT = Gauge('electrumx_sessions_count', 'Sessions count')
ELECTRUMX_SESSIONS_COUNT_WITH_SUBS = Gauge('electrumx_sessions_count_with_subs', 'Sessions counts with subs')
ELECTRUMX_SESSIONS_ERRORS = Gauge('electrumx_sessions_error', 'Sessions with errors')
ELECTRUMX_SESSIONS_LOGGED = Gauge('electrumx_sessions_logged', 'Sessions logged')
ELECTRUMX_SESSIONS_PENDING = Gauge('electrumx_sessions_pending', 'Sessions pending')
ELECTRUMX_SESSIONS_SUBS = Gauge('electrumx_sessions_subs', 'Sessions subs')

ELECTRUMX_TXS_SENT = Gauge('electrumx_txs_sent', 'Number of TXs sent ')

CONTENT_TYPE_LATEST = str('text/plain; version=0.0.4; charset=utf-8')

async def collect_metrics():
    try:
        async with timeout_after(timeout):
            async with connect_rs(rpc_host, rpc_port) as session:
                session.transport._framer.max_size = 0
                session.sent_request_timeout = timeout
                result = await session.send_request('getinfo', [])

                if insight_url is not None:
                    try:
                        loop = asyncio.get_event_loop()
                        insight_status = await loop.run_in_executor(None, requests.get, insight_url)
                        insight_status_json = insight_status.json()

                        ELECTRUMX_EXTERNAL_HEIGHT.set(insight_status_json['info']['blocks'])
                    except:
                        pass

                ELECTRUMX_DAEMON_HEIGHT.set(result['daemon height'])
                ELECTRUMX_DB_HEIGHT.set(result['db height'])
                ELECTRUMX_DB_FLUSH_COUNT.set(result['db_flush_count'])

                ELECTRUMX_PEERS_BAD.set(result['peers']['bad'])
                ELECTRUMX_PEERS_GOOD.set(result['peers']['good'])
                ELECTRUMX_PEERS_NEVER.set(result['peers']['never'])
                ELECTRUMX_PEERS_STALE.set(result['peers']['stale'])
                ELECTRUMX_PEERS_TOTAL.set(result['peers']['total'])

                ELECTRUMX_REQUESTS_TOTAL.set(result['request total'])

                ELECTRUMX_SESSIONS_COUNT.set(result['sessions']['count'])
                ELECTRUMX_SESSIONS_COUNT_WITH_SUBS.set(result['sessions']['count with subs'])
                ELECTRUMX_SESSIONS_ERRORS.set(result['sessions']['errors'])
                ELECTRUMX_SESSIONS_LOGGED.set(result['sessions']['logged'])
                ELECTRUMX_SESSIONS_PENDING.set(result['sessions']['pending requests'])
                ELECTRUMX_SESSIONS_SUBS.set(result['sessions']['subs'])

                ELECTRUMX_TXS_SENT.set(result['txs sent'])

                return generate_latest()
        return 0
    except OSError:
        print('cannot connect - is ElectrumX catching up, not running, or '
              f'is {rpc_port} the wrong RPC port?')
        return 1
    except Exception as e:
        print(f'error making request: {e}')
        return 1


@app.route('/metrics', methods=['GET'])
def get_data():
    metrics = collect_metrics()

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    metrics = loop.run_until_complete(collect_metrics())

    print(metrics)
    return Response(metrics, mimetype=CONTENT_TYPE_LATEST)

if __name__ == '__main__':
    app.run(host=bind_host, port=bind_port)
