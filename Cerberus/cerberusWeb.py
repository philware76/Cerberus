### Use FastAPI run <cerberusWeb.py> to start the web service
### This file is the main entry point for the Cerberus Test Manager web service.
import logging

from fastapi import FastAPI
from logConfig import setupLogging

from Cerberus.manager import Manager
from Cerberus.plugins.tests.baseTest import BaseTest

setupLogging(logging.DEBUG)

logging.info("Starting Web Service...")
app = FastAPI()

logging.info("Starting Cerberus Test Manager...")
manager = Manager()


@app.get("/")
async def read_root():
    return {"Message": "Welcome to Cerberus Test Manager"}


@app.get("/tests")
async def read_tests():
    return {"Tests": [test.name for test in manager.testPlugins.keys()]}


@app.get("/equipment")
async def read_equipment():
    return {"Equipment": [equip.name for equip in manager.equipPlugins.keys()]}


@app.get("/product")
async def read_equipment():
    return {"Products": [product.name for product in manager.productPlugins.keys()]}

@app.get("/test/{test_name}")
async def run_test(test_name: str):
    test: BaseTest
    try:
        test = manager.findTest(test_name)
        if not test:
            return {"Error": f"Test plugin '{test_name}' not found."}

        found, missing = manager.checkRequirements(test)
        if len(missing) > 0:
            logging.error(f"Current equipment does not meet the requirements for {test.name}")
            return {"Error": f"Current equipment does not meet the requirements for {test.name}"}
    except Exception as e:
        logging.error(f"Error creating or checking requirements for test '{test_name}': {e}")
        return {"Error": str(e)}

    logging.info(f"All required equipment for {test.name} is available.")
    test.initialise()
    await test.run()
    result = test.getResult()

    return {
        "Test Name": test.name,
        "Result": {
            "Name": result.name,
            "Status": result.status
        }
    }
