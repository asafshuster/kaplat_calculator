from fastapi import FastAPI, Query, Request, Request
from pydantic import BaseModel
from fastapi.responses import JSONResponse
from calculator import Calculator
import uvicorn

from logger import get_logger_level, set_logger_level, independent_logger, request_logger, stack_logger
from itertools import count
import time

request_counter = count(1)
app = FastAPI()
calculator = Calculator()

class IndependentCalcInput(BaseModel):
    arguments: list[int]
    operation: str

class StackInput(BaseModel):
    arguments: list[int]


@app.middleware("http")
async def log_requests(request: Request, call_next): # Added async for FastAPI middleware
    request_number = next(request_counter)
    start_time = time.time()
    request.state.request_number = request_number

    request_logger.info(
        f"Incoming request | #{request_number} | resource: {request.url.path} | HTTP Verb {request.method}",
        extra={"request_number": request_number}
    )

    response = await call_next(request) # Await the call_next

    # Check if this is the request that changed the log level
    # We only log duration here if it's not the /logs/level PUT request
    # For /logs/level PUT, the duration will be logged inside the endpoint function
    if not (request.url.path == "/logs/level" and request.method == "PUT"):
        duration_ms = int((time.time() - start_time) * 1000)
        request_logger.debug(
            f"request #{request_number} duration: {duration_ms}ms",
            extra={"request_number": request_number}
        )

    return response

@app.get("/calculator/health")
def health():
    return "OK"

@app.post("/calculator/independent/calculate")
def independent_calculate(data: IndependentCalcInput, request: Request):
    is_success, result = calculator.calc(data.arguments, data.operation)
    (code, field) = (200, "result") if is_success else (409, "errorMessage")

    if is_success:
        request_number = request.state.request_number
        independent_logger.info(
            f"Performing operation {data.operation}. Result is {result}",
            extra={"request_number": request_number}
        )
        independent_logger.debug(
            f"Performing operation: {data.operation}({','.join(map(str, data.arguments))}) = {result}",
            extra={"request_number": request_number}
        )
    else:
        independent_logger.error(f"Server encountered an error ! message: {result}")
    return JSONResponse(content={field: result}, status_code=code)

@app.get("/calculator/stack/size")
def stack_size(request: Request):
    request_number = request.state.request_number
    size = len(calculator.stack)

    stack_logger.info(f"Stack size is {size}", extra={"request_number": request_number})
    stack_logger.debug(f"Stack content (first == top): [{', '.join(map(str, calculator.stack[::-1]))}]",
                       extra={"request_number": request_number})
    return {"result": size}

@app.put("/calculator/stack/arguments")
def add_to_stack(data: StackInput, request: Request):
    request_number = request.state.request_number
    calculator.stack.extend(data.arguments)

    stack_logger.info(f"Adding total of {len(data.arguments)} argument(s) to the stack | Stack size: {len(calculator.stack)}",
                      extra={"request_number": request_number})
    stack_logger.debug(f"Adding arguments: {','.join(map(str, data.arguments))} | Stack size before {len(calculator.stack) - len(data.arguments)} | stack size after {len(calculator.stack)}",
                       extra={"request_number": request_number})

    return {"result": len(calculator.stack)}

@app.get("/calculator/stack/operate")
def stack_operate(request: Request, operation: str = Query(...)):
    is_success, result = calculator.calc(None, operation, is_independent=False)
    (code, field) = (200, "result") if is_success else (409, "errorMessage")

    request_number = request.state.request_number
    if is_success:
        stack_logger.info(
            f"Performing operation {operation}. Result is {result} | stack size: {len(calculator.stack)}",
            extra={"request_number": request_number}
        )
        stack_logger.debug(
            f"Performing operation: {operation}({','.join(map(str, calculator.get_last_calc('STACK').get('arguments')))}) = {result}",
            extra={"request_number": request_number}
        )
    else:
        stack_logger.error(
            f"Server encountered an error ! message: {result}",
            extra={"request_number": request_number}
        )
    return JSONResponse(content={field: result}, status_code=code)

@app.delete("/calculator/stack/arguments")
def delete_from_stack(request: Request, num_to_delete: int = Query(..., alias="count")):
    is_success, result = calculator.delete_from_stack(num_to_delete)
    (code, field) = (200, "result") if is_success else (409, "errorMessage")

    request_number = request.state.request_number
    stack_logger.info(
        f"Removing total {num_to_delete} argument(s) from the stack | Stack size: {result}",
        extra={"request_number": request_number}
    )
    return JSONResponse(content={field: result}, status_code=code)

@app.get("/calculator/history")
def get_history(request: Request, flavor: str = Query(None)):
    request_number = request.state.request_number
    flavor_upper = flavor.upper() if flavor else None

    if flavor_upper == "STACK":
        history = calculator.get_history("STACK")
        stack_logger.info(
            f"History: So far total {len(history)} stack actions",
            extra={"request_number": request_number}
        )

    elif flavor_upper == "INDEPENDENT":
        history = calculator.get_history("INDEPENDENT")
        independent_logger.info(
            f"History: So far total {len(history)} independent actions",
            extra={"request_number": request_number}
        )

    else:  # flavor is None
        history = calculator.get_history()  # combined list
        stack_count = len(calculator.get_history("STACK"))
        independent_count = len(calculator.get_history("INDEPENDENT"))

        stack_logger.info(
            f"History: So far total {stack_count} stack actions",
            extra={"request_number": request_number}
        )
        independent_logger.info(
            f"History: So far total {independent_count} independent actions",
            extra={"request_number": request_number}
        )

    return {"result": history}

@app.get("/logs/level")
def get_level(logger_name: str = Query(..., alias="logger-name")):
    level = get_logger_level(logger_name)
    if level is None:
        return JSONResponse(content="Logger not found", status_code=400)
    return level

@app.put("/logs/level")
def set_level(logger_name: str = Query(..., alias="logger-name"), logger_level: str = Query(..., alias="logger-level"), request: Request=None):
    # Capture start time here for accurate duration calculation for this specific request
    start_time = time.time()
    request_number = request.state.request_number # Get request_number here

    success = set_logger_level(logger_name, logger_level)
    if not success:
        return JSONResponse(content="Invalid logger name or level", status_code=400)

    # Log the duration for THIS specific request here, after the level has been set
    # This ensures the DEBUG message is logged immediately after the level change.
    duration_ms = int((time.time() - start_time) * 1000)
    # Use request_logger to log its own duration
    request_logger.debug(
        f"request #{request_number} duration: {duration_ms}ms",
        extra={"request_number": request_number}
    )

    return logger_level.upper()


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8496, reload=False)
