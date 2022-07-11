import json


class ApiHandler:
    def __init__(self):
        self.requests_queue = {}

    def add_request(self, request, args, handler=None):
        if not hasattr(request, '__call__'):
            return
        if not hasattr(handler, '__call__'):
            return
        self.requests_queue[request] = (args, handler)

    def do_requests(self):
        for request in self.requests_queue.keys():  # Adding the .keys operator to prevent runtime error when deleting elements from the same dict
            args = self.requests_queue[request][0]
            resp = request(**args)
            if resp is not None:
                resp_dict = json.loads(resp)
                if 'success' not in resp_dict:
                    break
                if not resp_dict['success']:
                    break
                handler = self.requests_queue[request][1]
                if handler is not None:
                    # call the handler and remove if response is successful
                    if self.requests_queue[request][1](resp):
                        del self.requests_queue[request]
                else:
                    if resp:
                        del self.requests_queue[request]




