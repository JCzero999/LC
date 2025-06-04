# DataMetrics Agent 快速开始指南

## 🚀 5分钟快速体验

### 1. 环境准备

```bash
# 克隆项目
git clone https://github.com/JCzero999/LC.git
cd LC

# 安装依赖
pip install -r requirements.txt

# 或使用Poetry
poetry install
```

### 2. 配置数据源

复制配置模板：
```bash
cp config/config.example.yaml config/config.yaml
```

编辑配置文件，添加你的数据库连接信息：
```yaml
databases:
  sources:
    my_database:
      type: mysql  # 或 postgresql, clickhouse
      host: localhost
      port: 3306
      database: your_database
      username: your_username
      password: your_password
```

### 3. 启动服务

#### 方式一：Web API服务
```bash
python -m datametrics_agent.main --mode server --port 8000
```

访问 http://localhost:8000/docs 查看API文档

#### 方式二：命令行工具
```bash
# 创建指标
python -m datametrics_agent.cli create-metric "每日活跃用户数" --data-source my_database

# 查询指标
python -m datametrics_agent.cli query-metric metric_001 --start-date 2024-01-01 --end-date 2024-01-31

# 列出所有指标
python -m datametrics_agent.cli list-metrics
```

### 4. 使用Python API

```python
from datametrics_agent import MetricsAgent, Config

# 初始化Agent
config = Config.from_yaml("config/config.yaml")
agent = MetricsAgent(config=config)

# 创建指标
metric = agent.create_metric(
    description="统计每日活跃用户数",
    data_source="my_database"
)

# 查询指标
result = agent.execute_metric(metric)
print(f"查询结果: {result.data}")

# 清理资源
agent.close()
```

## 📊 示例场景

### 电商业务指标

```python
# 1. 每日订单量
orders_metric = agent.create_metric(
    description="统计每日订单总数从orders表",
    data_source="ecommerce_db",
    dimensions=["date"]
)

# 2. 用户留存率
retention_metric = agent.create_metric(
    description="计算7天用户留存率",
    data_source="analytics_db"
)

# 3. 平均订单金额
aov_metric = agent.create_metric(
    description="计算平均订单金额按地区分组",
    data_source="ecommerce_db",
    dimensions=["region"]
)
```

### 数据质量监控

```python
from datametrics_agent.core.models import DataQualityCheck, DataQualityRule

# 创建数据质量检查
quality_check = DataQualityCheck(
    name="订单数据完整性检查",
    data_source="ecommerce_db",
    table_name="orders",
    rules=[
        DataQualityRule(
            name="订单金额非空",
            rule_type="not_null",
            column="amount",
            threshold=0.99
        )
    ]
)

# 运行质量检查
results = agent.check_data_quality([quality_check])
for result in results:
    print(f"{result.rule_name}: {'✅' if result.passed else '❌'}")
```

## 🐳 Docker部署

### 快速启动
```bash
# 构建并启动所有服务
docker-compose up -d

# 查看服务状态
docker-compose ps

# 查看日志
docker-compose logs datametrics-agent
```

### 服务访问
- DataMetrics Agent API: http://localhost:8000
- Grafana监控面板: http://localhost:3000 (admin/admin)
- Prometheus指标: http://localhost:9090

## 🔧 常见问题

### Q: 如何添加新的数据源？
A: 在配置文件中添加数据源配置，支持MySQL、PostgreSQL、ClickHouse等。

### Q: 如何自定义指标计算逻辑？
A: 使用自定义表达式：
```python
custom_metric = agent.create_metric(
    description="自定义业务指标",
    metric_type="custom",
    custom_expression="SUM(revenue) / COUNT(DISTINCT customer_id)"
)
```

### Q: 如何设置数据质量告警？
A: 配置质量检查规则和阈值，系统会自动监控并告警。

### Q: 支持哪些数据库？
A: 目前支持MySQL、PostgreSQL、ClickHouse，更多数据库支持正在开发中。

## 📚 更多资源

- [完整文档](docs/)
- [API参考](http://localhost:8000/docs)
- [示例代码](examples/)
- [最佳实践](docs/best-practices.md)

## 🆘 获取帮助

- 查看帮助: `python -m datametrics_agent.cli --help`
- 提交Issue: [GitHub Issues](https://github.com/JCzero999/LC/issues)
- 社区讨论: [Discussions](https://github.com/JCzero999/LC/discussions)

---

🎉 恭喜！你已经成功启动了DataMetrics Agent。开始创建你的第一个数据指标吧！