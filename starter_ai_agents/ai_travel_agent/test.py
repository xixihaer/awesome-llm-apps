

class MyTool(Tool):
    name = "hello"
    description = "test"

    def run(self, *args, **kwargs):
        return "ok"

print(MyTool().run())