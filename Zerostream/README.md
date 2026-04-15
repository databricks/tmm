# ZeroStream

A mobile sensor data streaming demo showcasing near-real-time data ingestion using **Zerobus** and **Lakebase** on the Databricks platform.

## What is ZeroStream?

ZeroStream collects sensor data from mobile devices (accelerometer, GPS, magnetometer) and streams it to Databricks Unity Catalog via **Zerobus**, a high-throughput ingestion service. The backend displays real-time data through two independent views:

- **Zerobus View**: Queries Unity Catalog Delta tables via Databricks SQL Warehouse
- **Lakebase View**: Queries replicated data via PostgreSQL-compatible Lakebase interface with interactive map visualization

## Key Technologies

- **Zerobus**: Low-latency streaming ingestion to Unity Catalog
- **Lakebase**: PostgreSQL-compatible interface for Unity Catalog data
- **Delta Lake**: ACID transactions with liquid clustering
- **Databricks Apps**: Serverless deployment for frontend and backend

## Blog Post

This code accompanies the blog post: [Building a Near-Real-Time Application with Zerobus Ingest and Lakebase](https://www.databricks.com/blog/building-near-real-time-application-zerobus-ingest-and-lakebase)

## Disclaimer

This source code is provided **as-is** for educational and demonstration purposes. It is not intended for production use without proper security review, error handling, and testing.

## Documentation

- [CLAUDE.md](CLAUDE.md) - Complete project documentation
- [ZEROBUS_SETUP_GUIDE.md](docs/ZEROBUS_SETUP_GUIDE.md) - Setup instructions
- [ARCHITECTURE.md](docs/ARCHITECTURE.md) - Architecture details

## License

See [LICENSE](../LICENSE) for details.
