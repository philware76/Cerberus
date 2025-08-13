# Use FastAPI run <cerberusWeb.py> to start the web service
# This file is the main entry point for the Cerberus Test Manager web service.
import logging

from fastapi import FastAPI
from logConfig import setupLogging

from Cerberus.executor import Executor
from Cerberus.plugins.products.baseProduct import BaseProduct
from Cerberus.plugins.tests.baseTest import BaseTest
from Cerberus.pluginService import PluginService

setupLogging(logging.DEBUG)

logging.info("Starting Web Service...")
app = FastAPI()

logging.info("Starting Cerberus Plugin Service...")
pluginService = PluginService()
executor = Executor(pluginService)


@app.get("/")
async def read_root():
    return {"Message": "Welcome to Cerberus Test Manager"}


@app.get("/tests")
async def read_tests():
    return {"Tests": list(pluginService.testPlugins.keys())}


@app.get("/equipment")
async def read_equipment():
    return {"Equipment": list(pluginService.equipPlugins.keys())}


@app.get("/product")
async def read_products():
    return {"Products": list(pluginService.productPlugins.keys())}


@app.get("/test/{test_name}")
async def run_test(test_name: str):
    test: BaseTest | None = pluginService.findTest(test_name)
    if not test:
        return {"Error": f"Test plugin '{test_name}' not found."}

    # Check requirements first (not initialised here)
    requirements = pluginService.getRequirements(test)
    if len(requirements.missing) > 0:
        logging.error(f"Current equipment does not meet the requirements for {test.name}: {requirements.missing}")
        return {"Error": f"Missing required equipment: {requirements.missing}"}

    # Execute via Executor (handles initialise/inject/finalise)
    ok = executor.runTest(test, BaseProduct("Product1"))
    result = test.getResult()

    return {
        "Test Name": test.name,
        "Passed": ok,
        "Result": None if result is None else {
            "Name": getattr(result, "name", None),
            "Status": getattr(result, "status", None),
        },
    }
