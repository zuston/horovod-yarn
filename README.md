Linked TonY(TF/PyTorch on Yarn) PR: https://github.com/linkedin/TonY/pull/524
## Horovod on Yarn
Aim to provide a Horovod local test program on Yarn, which can perform multi-process tests locally.

1. Driver start rendezvous server 
2. Inject some Horovod envs before starting training worker

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