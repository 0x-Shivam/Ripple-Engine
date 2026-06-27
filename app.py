from flask import Flask, request, jsonify
from flask_cors import CORS

from engine import ButterflyPredictionEngine


app = Flask(__name__)
CORS(app)  

engine = ButterflyPredictionEngine()


@app.route('/api/simulate', methods=['GET'])
def simulate():
    """
    API Endpoint that listens for requests from the frontend.
    Expects URL parameters: ?project=Proposed_Metro_Hub&year=2035
    """
    project = request.args.get('project', 'Proposed_Metro_Hub')

    year_str = request.args.get('year', '2035')
    
    print(f" Received API Request -> Project: {project}, Year Input: {year_str}")

    try:
        year = int(year_str)

    except (ValueError, TypeError):
        print("⚠️ Invalid year format received. Defaulting to 2035.")
        year = 2035

    metrics_result = {}

    try:
        

        metrics_result = engine.calculate_predictions(project, target_year=year)
    except Exception as e:
        print(f" Core Engine Failure during execution: {str(e)}")
        return jsonify({
            "status": "error",

            "message": f"Calculation failed: {str(e)}"
        }), 500
    
    return jsonify({
        "status": "success",
        "parameters": {
            "project": project,
            
            "year": year
        },
        "data": metrics_result
    })


if __name__ == '__main__':
    app.run(debug=True, port=5001)