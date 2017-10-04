from time import sleep
from n4s.submodule import s

# http://avilpage.com/2017/05/how-to-auto-reload-celery-workers-in-development.html

def main(cfg):
    print(cfg)
    s(3)
    print("done")
