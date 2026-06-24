# Network-aware multi-agent reinforcement learning for P2P energy trading

This study investigates peer-to-peer energy trading among prosumers in an IEEE 33-bus distribution network.
The market uses double auction clearing and compares no trading, rule-based bidding, optimization clearing,
and multi-agent reinforcement learning. Agent states include PV generation, load, battery SOC, time-of-use
price, and voltage. Actions include buy/sell/hold, bid quantity, bid price, and storage dispatch. The reward
minimizes energy cost and carbon emissions while penalizing voltage violations and network loss.

The paper reports cost, P2P trading volume, carbon emissions, social welfare, voltage violations, and network
loss, but does not provide source code or full hyperparameters.

