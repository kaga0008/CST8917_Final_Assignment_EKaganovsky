import azure.functions as func
import azure.durable_functions as df
import logging
import json

#                               |---> validate expenses ---v
# start workflow --> orchestrator --> notify manager --------->
#                               |---> get manager approval-^
#
app = df.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)

VALID_CATEGORIES = ["travel", "meals", "supplies", "equipment", "software", "other"]
REQUIRED_FIELDS = ["employee_name", "employee_email", "amount", "category", "description", "manager_email"]


# Workflow triggered by an HTTP request to start the expense approval process. 
# The request body should contain the expense details.
@app.route(route="make_request", methods=["POST"])
@app.durable_client_input(client_name="client")
async def intake_request(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Python HTTP trigger function processed a request.')

    # Attempt to parse incoming request into a valid JSON object
    try:
        request_data = req.get_json()
    except ValueError:
        return func.HttpResponse(
            json.dumps({"ERROR": "Invalid JSON in request body."}),
            status_code=400,
            mimetype="application/json"
        )

    name = req.params.get('name')
    if not name:
        try:
            req_body = req.get_json()
        except ValueError:
            pass
        else:
            name = req_body.get('name')

    if name:
        return func.HttpResponse(f"Hello, {name}. This HTTP triggered function executed successfully.")
    else:
        return func.HttpResponse(
             "This HTTP triggered function executed successfully. Pass a name in the query string or in the request body for a personalized response.",
             status_code=200
        )
    
# Orchestrator function that defines the workflow for processing an expense approval request.
# Calls activity functions to:
#   - Validate expenses
#   - Notify the manager of the request
@app.orchestration_trigger(context_name="context")
async def expense_approval_orchestrator(context: df.DurableOrchestrationContext):
    request_data = context.get_input()
    
    # Validate expenses
    validation_result = await context.call_activity("validate_expenses", request_data)
    if not validation_result["is_valid"]:
        return {"status": "rejected", "reason": "Invalid expenses"}

    # Notify manager
    await context.call_activity("notify_manager", request_data)

    # Get manager approval
    approval_result = await context.call_activity("get_manager_approval", request_data)
    if approval_result["approved"]:
        return {"status": "approved"}
    else:
        return {"status": "rejected", "reason": "Manager disapproved"}


@app.activity_trigger(input_name="request_data")
def validate_expenses(request_data):

    # Check for missing fields
    missing_fields = [field for field in REQUIRED_FIELDS if field not in request_data.get(field)]
    if missing_fields:
        return {"is_valid": False, 
                "reason": f"Missing fields: {', '.join(missing_fields)}"
                }
    
    # Check for invalid category
    category = str(request_data["category"]).lower()
    if category not in VALID_CATEGORIES:
        return {
            "is_valid": False,
            "message": f"Invalid category: {category}. Valid categories: {', '.join(VALID_CATEGORIES)}"
        }
    
    try:
        # Check for invalid amount
        amount = float(request_data["amount"])
        if amount <= 0:
            return {"is_valid": False, 
                    "reason": "Amount must be greater than zero"
                    }
    except ValueError:
        # Check for non-numeric amount
        return {"is_valid": False, 
                "reason": "Amount must be a valid number"
                }
    
    # If all validations pass, return valid response :)
    return {"is_valid": True,
            "message": "Expenses are valid. Yay!"}


@app.activity_trigger(input_name="request_data")
def notify_manager(request_data):
    pass

@app.activity_trigger(input_name="request_data")
def get_manager_approval(request_data):
    pass