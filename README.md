## Horovod on Yarn
旨在提供一个 horovod on Yarn 的方案。此方案可以在本地进行多进程的测试

1. driver 启动一个 rendevous server 
2. 各个 worker 通过注入一些 horovod 运行时变量，即可启动