from Cerberus.cmdShells.baseShell import BaseShell
from Cerberus.manager import Manager
from Cerberus.plugins.products.nesiePIC import NesiePIC


class PICShell(BaseShell):
    def __init__(self, manager: Manager, productName: str, picIPAddress: str):
        super().__init__(manager)

        PICShell.intro = "Cerberus PIC Shell. Type help or ? to list commands."
        PICShell.prompt = f"{productName} PIC@{picIPAddress}> "

        self.pic: NesiePIC | None = None

        self.productName = productName
        self.picIPAddress = picIPAddress
        self.daIPAddress: str

        self.do_getStatus("")

    def runLoop(self) -> str | None:
        """Runs the command loop and returns the DA IP Address on exit"""
        super().cmdloop()
        return self.daIPAddress

    def do_getStatus(self, arg):
        """Get the status of the device"""
        pic = NesiePIC(self.picIPAddress)
        if pic is None:
            print("Failed to get PIC status")
            return

        self.pic = pic
        powerState = self.pic["PowerState"]
        self.daIPAddress = self.pic["daaddress"]
        print(f"""
            Power state: {"ON" if powerState == 8 else "OFF" if powerState == 0 else "Booting..."}
            DA Address : {"Not available" if self.daIPAddress == "0.0.0.0" else self.daIPAddress}
            Temperature: {self.pic["temperature"]}

              """)

        if self.daIPAddress != "0.0.0.0":
            print("You can exit back as we have the DA Address")

    def do_getDA(self, arg):
        """Get the DA Address and store it for later use with openDA command"""
        if self.pic is None:
            print("Please run getStatus first")
            return

        self.daIPAddress = self.pic["daaddress"]
        if self.daIPAddress == "0.0.0.0":
            print("DA board not ready yet... please wait for PowerState: 8")
            return

        print("DA IP Address: " + self.daIPAddress)

    def do_powerOn(self, arg):
        """Powers on the devce"""
        if self.pic is None:
            print("Please run getstatus first")
            return

        if not self.pic.powerOn():
            print("Failed to request for power on")

        if arg is not None:

            def _timeoutFunc(timeTaken: int):
                print(".", end="")
                return timeTaken < 90

            if self.pic.waitForPowerOn(_timeoutFunc):
                print("\nPowered On")
            else:
                print("\nTimed out waiting for device to boot.")

    def do_powerOff(self, arg):
        """Powers off the device"""
        if self.pic is None:
            print("Please run getstatus first")
            return

        if not self.pic.powerOff():
            print("Failed to request for power off")

        if arg is not None:
            def _timeoutFunc(timeTaken: int):
                print(".", end="")
                return timeTaken < 90

            if self.pic.waitForPowerOff(_timeoutFunc):
                print("\nPowered Off")
            else:
                print("\nTimed out waiting for device to power off.")
