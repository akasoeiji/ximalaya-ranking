.PHONY: run run3 docker-build docker-run schedule

run:            ## 完整跑一次(50页)
	python -m xmr.run_all

run3:           ## 小规模快速验证(3页30主播)
	python -m xmr.run_all --pages 3 --max-anchors 30

docker-build:   ## 构建镜像
	docker build -t totootao/ximalaya-ranking:latest .

docker-run:     ## 手动跑一次并输出到 ./output
	docker run --rm -v $$PWD/output:/app/output totootao/ximalaya-ranking:latest

schedule:       ## 定时模式(每天一轮)
	docker run --rm -e RUN_MODE=schedule -e SCHEDULE_INTERVAL_SECONDS=86400 -v $$PWD/output:/app/output totootao/ximalaya-ranking:latest
