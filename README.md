## Horovod on Yarn
旨在提供一个 horovod on Yarn 的方案。此方案可以在本地进行多进程的测试

1. driver 启动一个 rendevous server 
2. 各个 worker 通过注入一些 horovod 运行时变量，即可启动

__Driver__
```
python3 driver.py -w localhost:2
```

__Task__
```
python3 tensorflow2_minist.py --port=34824 --rank=0 --size=2 --local_rank=0 --local_size=2 --cross_rank=0 --cross_size=1  
```

```
python3 tensorflow2_minist.py --port=34824 --rank=1 --size=2 --local_rank=1 --local_size=2 --cross_rank=0 --cross_size=1
```