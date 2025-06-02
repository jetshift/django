import json
from django.http import HttpResponse


def dd(*args):
    content = "<pre>"
    for arg in args:
        try:
            content += json.dumps(arg, indent=2, ensure_ascii=False)
        except TypeError:
            content += str(arg)
        content += "\n\n"
    content += "</pre>"
    return HttpResponse(content)
