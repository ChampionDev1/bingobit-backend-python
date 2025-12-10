Python-based multi-chain core services for Solana, Ethereum, and BSC. Handles deposits, withdrawals, buys, sells, cross-chain swap orchestration, system wallet operations, and coin chat. Structured as a microservice monorepo and integrated with Go gateway and TS data services.

## Project Structure

```
.
├── common/                          # Shared utilities and configurations
│   ├── config.py                   # Central configuration
│   ├── database.py                 # Database operations
│   ├── kafka_producer.py           # Kafka event producer
│   ├── logger.py                   # Logging setup
│   └── utils.py                    # Utility functions
├── database/
│   └── schema.sql                  # Database schema
├── proto/                          # Protocol buffer definitions
│   ├── onchain.proto              # OnChain service definitions
│   └── systemwallet.proto         # SystemWallet service definitions
├── scripts/                        # Setup and testing scripts
│   ├── setup_test_env.py          # Initialize test environment
│   └── test_deposit_flow.py       # Test deposit functionality
├── services/
│   ├── onchain_service/           # Blockchain operations service
│   │   ├── blockchain/            # Blockchain client implementations
│   │   │   └── solana_client.py  # Solana RPC client
│   │   ├── monitors/              # Transaction monitoring
│   │   │   └── deposit_monitor.py # Deposit monitoring service
│   │   ├── processors/            # Transaction processors
│   │   │   └── deposit.py        # Deposit processor
│   │   ├── main.py               # Service entry point
│   │   └── requirements.txt      # Python dependencies
│   ├── systemwallet_service/      # System wallet management
│   │   ├── main.py
│   │   ├── wallet_manager.py
│   │   └── requirements.txt
│   ├── swap_service/              # Cross-chain swap orchestration
│   └── chat_service/              # Coin chat functionality
├── tests/
│   └── test_deposit.py
├── .env.example                    # Environment configuration template
├── docker-compose.yml              # Docker services for testing
└── DEPOSIT_IMPLEMENTATION.md       # Detailed implementation guide

```

## Features

### ✅ Implemented: Solana Deposit System

- **Automatic Deposit Monitoring**: Continuously monitors deposit addresses for incoming transactions
- **Smart Sweep Operations**: Automatically transfers deposits to hot wallet
- **Edge Case Handling**: Handles insufficient fee scenarios by injecting fees from hot wallet
- **Real-time Events**: Broadcasts deposit status via Kafka to Go API Gateway
- **Production-Ready**: Comprehensive error handling, retry logic, and logging
- **Devnet Testing**: Full testing suite for Solana devnet

### 🚧 Planned

- Ethereum deposit monitoring
- BSC deposit monitoring
- Withdrawal processing
- Buy/Sell operations
- Cross-chain swaps

## Quick Start

### Prerequisites

- Python 3.9+
- PostgreSQL 15+
- Redis 7+
- Kafka 3.5+
- Solana CLI (for testing)

### Installation

1. **Clone and setup environment**
```bash
git clone <repository>
cd <project>
cp .env.example .env
# Edit .env with your configuration
```

2. **Install dependencies**
```bash
pip install -r services/onchain_service/requirements.txt
pip install -r services/systemwallet_service/requirements.txt
```

3. **Start infrastructure services**
```bash
docker-compose up -d
```

4. **Initialize database and test environment**
```bash
python scripts/setup_test_env.py
```

This will:
- Create database tables
- Generate test deposit addresses
- Display hot wallet configuration

5. **Fund hot wallet with devnet SOL**
```bash
# Get SOL from faucet
solana airdrop 2 <HOT_WALLET_ADDRESS> --url devnet
```

### Running Services

**Terminal 1 - SystemWallet Service:**
```bash
python services/systemwallet_service/main.py
```

**Terminal 2 - OnChain Service (includes deposit monitor):**
```bash
python services/onchain_service/main.py
```

### Testing Deposits

**Automated test:**
```bash
python scripts/test_deposit_flow.py --amount 0.1
```

**Manual test:**
1. Get a test deposit address from setup output
2. Send SOL to the address:
```bash
solana transfer <DEPOSIT_ADDRESS> 0.1 --url devnet
```
3. Watch the onchain_service logs for automatic processing

## Deposit Flow

1. **User deposits** → SOL sent to user's deposit address
2. **Detection** → Monitor detects transaction on blockchain
3. **Confirmation** → Waits for minimum confirmations (15 blocks)
4. **Sweep** → Automatically transfers to hot wallet
   - Normal case: Direct transfer
   - Edge case: Injects fee first if insufficient balance
5. **Completion** → Updates system wallet balance, broadcasts event

## Configuration

Key environment variables in `.env`:

```bash
# Solana Network
SOLANA_RPC_URL=https://api.devnet.solana.com
SOLANA_NETWORK=devnet

# Hot Wallet (KEEP SECURE!)
SOLANA_HOT_WALLET_ADDRESS=<your_address>
SOLANA_HOT_WALLET_PRIVATE_KEY=<your_private_key>

# Transaction Settings
MIN_CONFIRMATIONS=15
TRANSACTION_TIMEOUT=60
MIN_DEPOSIT_AMOUNT=10000000  # 0.01 SOL in lamports

# Database
DB_HOST=localhost
DB_NAME=crypto_platform
DB_USER=postgres
DB_PASSWORD=postgres

# Kafka
KAFKA_BOOTSTRAP_SERVERS=localhost:9092
```

## Architecture

### Services

- **OnChain Service** (port 50051): Blockchain operations and deposit monitoring
- **SystemWallet Service** (port 50052): System wallet balance management
- **Swap Service**: Cross-chain swap orchestration (planned)
- **Chat Service**: Coin chat functionality (planned)

### Communication

- **gRPC**: Inter-service communication
- **Kafka**: Event broadcasting to Go API Gateway
- **PostgreSQL**: Transaction and address storage
- **Redis**: Caching and session management

## Documentation

📚 **[INDEX.md](INDEX.md)** - Complete documentation index and navigation guide

- **[QUICKSTART.md](QUICKSTART.md)**: Get started in 10 minutes
  - Step-by-step setup guide
  - Quick testing instructions
  - Troubleshooting basics

- **[DEPOSIT_IMPLEMENTATION.md](DEPOSIT_IMPLEMENTATION.md)**: Complete technical documentation
  - Architecture details
  - Edge case handling
  - Production considerations
  - API integration guide

- **[TESTING_GUIDE.md](TESTING_GUIDE.md)**: Comprehensive testing guide
  - Test scenarios
  - Monitoring tools
  - Performance testing
  - Troubleshooting

- **[PROJECT_SUMMARY.md](PROJECT_SUMMARY.md)**: Implementation overview
  - What was built
  - Technical decisions
  - Code quality standards
  - Deployment guide

## Development

### Generate Protocol Buffers

**Linux/Mac:**
```bash
chmod +x scripts/generate_proto.sh
./scripts/generate_proto.sh
```

**Windows:**
```bash
scripts\generate_proto.bat
```

### Running Tests

```bash
pytest tests/
```

## Production Deployment

### Security Checklist

- [ ] Encrypt private keys in database
- [ ] Use secure key management (HSM/KMS)
- [ ] Enable SSL/TLS for all connections
- [ ] Implement rate limiting
- [ ] Add authentication/authorization
- [ ] Secure RPC endpoints
- [ ] Enable audit logging

### Monitoring

- [ ] Set up Prometheus metrics
- [ ] Configure alerts for failures
- [ ] Monitor sweep success rate
- [ ] Track confirmation times
- [ ] Balance monitoring
- [ ] Transaction reconciliation

### Scalability

- [ ] Horizontal scaling of monitors
- [ ] Database connection pooling
- [ ] Redis caching layer
- [ ] Kafka consumer groups
- [ ] Load balancing

## Troubleshooting

**Deposits not detected?**
- Check RPC connectivity
- Verify deposit addresses in database
- Ensure monitor is running

**Sweep failures?**
- Verify hot wallet balance
- Check private key configuration
- Review network status

**Kafka events not received?**
- Check Kafka broker status
- Verify topic exists
- Review consumer configuration

See [DEPOSIT_IMPLEMENTATION.md](DEPOSIT_IMPLEMENTATION.md) for detailed troubleshooting.

## License

[Your License]

## Support

For issues or questions, please check the documentation or open an issue.

