# agent_orchestrator.py - IMPROVED WITH CONFIGURATION & ENHANCED ERROR HANDLING
import pandas as pd
import time
import logging
from datetime import datetime, timedelta
from typing import List, Dict

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class OrchestratorAgent:
    def __init__(self, api_key: str, api_secret: str, testnet: bool = True,
                 cycle_interval: int = 300, max_positions: int = 3, 
                 daily_loss_limit: float = 0.05, symbols: list = None):
        
        from trading_agents import MarketAnalysisAgent, RiskManagementAgent
        from agent_execution import ExecutionAgent
        
        # Set default symbols if none provided
        if symbols is None:
            symbols = ['BTC/USDT:USDT', 'ETH/USDT:USDT', 'ADA/USDT:USDT']
            
        self.analyst = MarketAnalysisAgent()
        self.guardian = RiskManagementAgent()
        self.executor = ExecutionAgent(api_key, api_secret, testnet)
        self.exchange = self.executor.exchange
        
        # Trading configuration - using passed parameters
        self.cycle_interval = cycle_interval
        self.max_positions = max_positions
        self.daily_loss_limit = daily_loss_limit
        self.symbols = symbols
        
        # Position sizing configuration (set from main.py)
        self.default_position_size = 0.01  # 1% default
        self.position_sizes = {}  # Will be populated from main.py
        
        # Enhanced portfolio tracking
        self.initial_balance = self.get_account_balance()
        self.portfolio_value = self.initial_balance
        self.open_positions = []
        self.trade_history = []
        self.daily_pnl = 0
        
        logger.info(f"Orchestrator initialized with: {max_positions} max positions, "
                   f"{daily_loss_limit:.1%} daily loss limit, {len(symbols)} symbols")

    def get_market_data(self, symbol: str = 'BTC/USDT:USDT', timeframe: str = '1h', limit: int = 100) -> pd.DataFrame:
        """Fetch market data with enhanced error handling"""
        try:
            ohlcv = self.exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df['symbol'] = symbol
            return df
        except Exception as e:
            logger.error(f"Market data fetch failed for {symbol}: {e}")
            # Return empty DataFrame with expected structure
            return pd.DataFrame(columns=['timestamp', 'open', 'high', 'low', 'close', 'volume', 'symbol'])
    
    def get_account_balance(self) -> float:
        """Get account balance using execution agent's enhanced method"""
        try:
            balance = self.executor.get_account_balance()
            logger.info(f"Account balance: {balance:.2f} USDT")
            return balance
        except Exception as e:
            logger.error(f"Balance fetch failed: {e}")
            return 1000.0  # Fallback for testing
    
    def _get_position_size_for_symbol(self, symbol: str) -> float:
        """Get the appropriate position size for a symbol"""
        if self.position_sizes and symbol in self.position_sizes:
            return self.position_sizes[symbol]
        return self.default_position_size
    
    def _enhance_trade_signal(self, trade_signal: Dict, symbol: str) -> Dict:
        """Enhance trade signal with proper position sizing and validation"""
        # Set symbol if not present
        if 'symbol' not in trade_signal:
            trade_signal['symbol'] = symbol
            
        # Override position size with configured size
        configured_size = self._get_position_size_for_symbol(symbol)
        trade_signal['position_size'] = configured_size
        
        # Ensure all required fields are present
        required_fields = ['type', 'position_size', 'stop_loss', 'take_profit']
        for field in required_fields:
            if field not in trade_signal:
                logger.warning(f"Trade signal missing required field: {field}")
                
        return trade_signal
    
    def cleanup_closed_positions(self):
        """Remove positions that have been closed"""
        active_positions = []
        for position in self.open_positions:
            try:
                # Check if stop loss or take profit was triggered
                order_id = position.get('order_id')
                if order_id and order_id in self.executor.positions:
                    active_positions.append(position)
                else:
                    # Calculate PnL for closed position
                    if 'executed_price' in position and 'current_price' in position:
                        pnl = (position['current_price'] - position['executed_price']) * position['amount']
                        if position['side'] == 'sell':
                            pnl = -pnl
                        position['pnl'] = pnl
                    
                    self.trade_history.append(position)
                    logger.info(f"Position closed: {position['symbol']} - PnL: {position.get('pnl', 'N/A')}")
            except Exception as e:
                logger.error(f"Error checking position {position.get('order_id')}: {e}")
        
        self.open_positions = active_positions
    
    def run_one_cycle(self):
        """Enhanced trading cycle with configurable position management"""
        logger.info("--- Starting Trading Cycle ---")
        
        # 1. Clean up closed positions
        self.cleanup_closed_positions()
        
        # 2. Get market data for configured symbols
        market_data = {}
        
        for symbol in self.symbols:  # ✅ Use configured symbols
            data = self.get_market_data(symbol)
            if not data.empty:
                market_data[symbol] = data
            else:
                logger.warning(f"No market data for {symbol}")
        
        if not market_data:
            logger.error("No market data available for any symbol. Skipping cycle.")
            time.sleep(60)
            return
        
        # 3. Update portfolio value using enhanced balance method
        try:
            current_balance = self.get_account_balance()
            balance_change = current_balance - self.portfolio_value
            self.portfolio_value = current_balance
            
            if balance_change != 0:
                logger.info(f"Portfolio update: {self.portfolio_value:.2f} USDT "
                           f"({balance_change:+.2f} change)")
        except Exception as e:
            logger.error(f"Failed to update portfolio value: {e}")
            # Continue with previous portfolio value
        
        # 4. Check risk limits before any trading
        emergency_stop = self.guardian.check_daily_loss_limit(
            self.portfolio_value, 
            self.initial_balance,
            self.daily_loss_limit  # ✅ Use configured loss limit
        )
        if emergency_stop:
            logger.critical(f"🚨 TRADING HALTED: {emergency_stop['reason']}")
            return
        
        # 5. Generate and validate signals
        approved_trades = []
        for symbol, data in market_data.items():
            # ✅ Use configured max_positions
            if len(self.open_positions) >= self.max_positions:
                logger.info(f"Max positions ({self.max_positions}) reached - skipping new trades")
                break
                
            # Generate signals
            volume_data = data['volume']
            potential_trades = self.analyst.generate_signals(data, volume_data, 'H1', self.position_sizes)
            
            # Risk validation and enhancement
            for trade in potential_trades:
                enhanced_trade = self._enhance_trade_signal(trade, symbol)
                approved_trade = self.guardian.validate_trade(
                    enhanced_trade, 
                    self.portfolio_value, 
                    self.open_positions
                )
                # Only accept trades with good risk scores
                if approved_trade['risk_score'] < 0.7:
                    approved_trades.append(approved_trade)
                    position_size_pct = approved_trade['position_size'] * 100
                    logger.info(f"✅ Approved trade: {symbol} {trade['type']} "
                               f"(risk: {approved_trade['risk_score']:.2f}, size: {position_size_pct:.1f}%)")
                else:
                    logger.info(f"❌ Rejected trade: {symbol} {trade['type']} "
                               f"(risk score: {approved_trade['risk_score']:.2f})")
        
        # 6. Execute approved trades
        executed_count = 0
        for trade in approved_trades:
            # Double-check position limit before execution
            if len(self.open_positions) >= self.max_positions:
                logger.warning(f"Max positions ({self.max_positions}) reached during execution")
                break
                
            result = self.executor.execute_trade(trade)
            if result['status'] == 'success':
                # Get execution price for tracking
                executed_price = self.executor.get_current_price(trade['symbol'])
                
                trade.update({
                    'order_id': result['order_id'],
                    'stop_loss_id': result['stop_loss_id'],
                    'take_profit_id': result['take_profit_id'],
                    'timestamp': pd.Timestamp.now(),
                    'executed_price': executed_price,
                    'position_size': trade.get('position_size', 0),
                    'amount': trade.get('position_size', 0)  # For consistency
                })
                self.open_positions.append(trade)
                executed_count += 1
                
                position_size_pct = trade['position_size'] * 100
                logger.info(f"🎯 Trade executed: {trade['symbol']} {trade['type']} "
                           f"Size: {position_size_pct:.1f}% @ {executed_price}")
            else:
                logger.error(f"💥 Trade execution failed: {trade['symbol']} - {result['message']}")
        
        # 7. Log cycle summary
        logger.info(f"🔄 Cycle complete. Executed {executed_count} trades. "
                   f"Open positions: {len(self.open_positions)}/{self.max_positions}")
        
        # Update current prices for open positions
        for position in self.open_positions:
            try:
                current_price = self.executor.get_current_price(position['symbol'])
                if current_price:
                    position['current_price'] = current_price
            except Exception as e:
                logger.warning(f"Could not update price for {position['symbol']}: {e}")
    
    def run_continuously(self, cycle_interval_seconds: int = None):
        """Main loop with proper interval control"""
        # Use configured interval if none provided
        if cycle_interval_seconds is None:
            cycle_interval_seconds = self.cycle_interval
            
        logger.info(f"🚀 Starting continuous trading with {cycle_interval_seconds}s intervals")
        logger.info(f"📊 Trading {len(self.symbols)} symbols: {', '.join(self.symbols)}")
        logger.info(f"⚙️  Configuration: {self.max_positions} max positions, "
                   f"{self.daily_loss_limit:.1%} daily loss limit")
        
        if self.position_sizes:
            size_info = ", ".join([f"{sym}: {size*100:.1f}%" for sym, size in self.position_sizes.items()])
            logger.info(f"💰 Position sizes: {size_info}")
        else:
            logger.info(f"💰 Default position size: {self.default_position_size*100:.1f}%")
        
        cycle_count = 0
        while True:
            cycle_count += 1
            cycle_start = time.time()
            
            try:
                logger.info(f"\n📈 Cycle #{cycle_count} starting at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                self.run_one_cycle()
            except Exception as e:
                logger.error(f"💥 Unexpected error in trading cycle #{cycle_count}: {e}")
                time.sleep(60)  # Wait longer on errors
                continue
            
            # Precise interval timing
            cycle_duration = time.time() - cycle_start
            sleep_time = max(1, cycle_interval_seconds - cycle_duration)
            
            if sleep_time > 1:
                logger.info(f"⏰ Cycle completed in {cycle_duration:.1f}s. "
                           f"Sleeping for {sleep_time:.1f}s until next cycle.")
            else:
                logger.info(f"⚡ Cycle completed in {cycle_duration:.1f}s. "
                           f"Starting next cycle immediately.")
                
            time.sleep(sleep_time)
    
    def get_performance_summary(self) -> Dict:
        """Get current performance summary"""
        total_pnl = self.portfolio_value - self.initial_balance
        total_pnl_percent = (total_pnl / self.initial_balance * 100) if self.initial_balance > 0 else 0
        
        # Calculate additional metrics
        winning_trades = len([t for t in self.trade_history if t.get('pnl', 0) > 0])
        losing_trades = len([t for t in self.trade_history if t.get('pnl', 0) < 0])
        
        return {
            'initial_balance': self.initial_balance,
            'current_balance': self.portfolio_value,
            'total_pnl': total_pnl,
            'total_pnl_percent': total_pnl_percent,
            'open_positions': len(self.open_positions),
            'total_trades': len(self.trade_history),
            'winning_trades': winning_trades,
            'losing_trades': losing_trades,
            'win_rate': (winning_trades / len(self.trade_history) * 100) if self.trade_history else 0,
            'max_positions': self.max_positions,
            'daily_loss_limit': self.daily_loss_limit,
            'trading_symbols': self.symbols,
            'position_sizes': self.position_sizes
        }