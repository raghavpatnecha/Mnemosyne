from quart import Quart, render_template, Response
from quart_cors import cors
from src.api.search import decode_query, stream_response

app = Quart(__name__, template_folder='./templates', static_folder=''
                                                                   './static')
app = cors(app)

@app.route('/')
async def home():
    return await render_template('index.html')

@app.route('/mnemosyne/api/v1/search/<query>')
async def search(query: str) -> Response:
    """Handle search requests."""
    final_query = decode_query(query)
    return Response(
        stream_response(final_query),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'X-Accel-Buffering': 'no'
        }
    )

if __name__ == '__main__':
    app.run()