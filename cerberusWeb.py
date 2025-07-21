import logging

from logConfig import setupLogging
from plugins.tests.baseTest import BaseTest
from testManager import TestManager

from fastapi import FastAPI

setupLogging(logging.DEBUG)

logging.info("Starting Web Service...")
app = FastAPI()

logging.info("Starting Cerberus Test Manager...")
manager = TestManager()


@app.get("/")
async def read_root():
    return {"Message": "Welcome to Cerberus Test Manager"}


@app.get("/tests")
async def read_tests():
    return {"Tests": [test.name for test in manager.tests]}


@app.get("/equipment")
async def read_equipment():
    return {"Equipment": [equip.name for equip in manager.equipment]}


@app.get("/test/{test_name}")
async def run_test(test_name: str):
    try:
        test: BaseTest = manager._testPlugins.getPlugin(test_name)
        if not test:
            return {"Error": f"Test plugin '{test_name}' not found."}

        equipment = manager.checkRequirements(test)
        if not equipment:
            logging.error(f"Current equipment does not meet the requirements for {test.name}")
            return {"Error": f"Current equipment does not meet the requirements for {test.name}"}
    except Exception as e:
        logging.error(f"Error creating or checking requirements for test '{test_name}': {e}")
        return {"Error": str(e)}

    logging.info(f"All required equipment for {test.name} is available.")
    test.Initialise()
    await test.run()
    result = test.getResult()

    return {
        "Test Name": test.name,
        "Result": {
            "Name": result.name,
            "Status": result.status
        }
    }
