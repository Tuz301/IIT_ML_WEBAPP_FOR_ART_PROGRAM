# trading_agents.py - FUSED ENHANCED VERSION WITH CONFIGURED POSITION SIZING
import pandas as pd
import numpy as np
import logging
from typing import List, Dict
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class TradeSignal:
    symbol: str
    type: str  # 'BUY' or 'SELL'
    position_size: float
    stop_loss: float
    take_profit: float
    confidence: float = 0.0
    volatility: float = 0.0

class MarketAnalysisAgent:
    def __init__(self):
        self.volume_threshold = 1.5  # Volume spike threshold
        self.price_change_threshold = 0.02  # 2% price movement
        
    def generate_signals(self, market_data: pd.DataFrame, volume_data: pd.Series, 
                        timeframe: str, position_sizes: dict = None) -> List[Dict]:
        """Generate trading signals using configured position sizes"""
        try:
            signals = []
            
            if market_data.empty:
                return signals
            
            # Extract symbol from market data
            symbol = market_data['symbol'].iloc[0] if 'symbol' in market_data.columns else 'BTC/USDT:USDT'
            
            # Use configured position sizes if available, otherwise defaults
            default_size = 0.01  # 1% default
            
            if position_sizes and symbol in position_sizes:
                position_size = position_sizes[symbol]
                logger.info(f"Using configured position size for {symbol}: {position_size:.1%}")
            else:
                position_size = default_size
                logger.info(f"Using default position size for {symbol}: {position_size:.1%}")
            
            # Calculate technical indicators
            market_data = self._calculate_indicators(market_data)
            
            # Get current price and volume
            current_price = market_data['close'].iloc[-1]
            current_volume = volume_data.iloc[-1]
            avg_volume = volume_data.tail(20).mean()
            
            # Strategy 1: Volume Spike + Price Momentum
            if current_volume > avg_volume * self.volume_threshold:
                price_change = (current_price - market_data['close'].iloc[-2]) / market_data['close'].iloc[-2]
                
                if abs(price_change) > self.price_change_threshold:
                    signal_type = 'BUY' if price_change > 0 else 'SELL'
                    
                    # Calculate stop loss and take profit using configured position size
                    if signal_type == 'BUY':
                        stop_loss = current_price * 0.98  # 2% stop loss
                        take_profit = current_price * 1.03  # 3% take profit
                    else:
                        stop_loss = current_price * 1.02  # 2% stop loss
                        take_profit = current_price * 0.97  # 3% take profit
                    
                    # Calculate confidence based on volume and momentum
                    confidence = min(0.9, (current_volume / avg_volume - 1) * abs(price_change) * 10)
                    
                    signal = {
                        'symbol': symbol,  # Ensure symbol is included
                        'type': signal_type,
                        'position_size': position_size,  # Use configured size
                        'stop_loss': stop_loss,
                        'take_profit': take_profit,
                        'confidence': confidence,
                        'volatility': abs(price_change)
                    }
                    signals.append(signal)
            
            # Strategy 2: Simple Moving Average Crossover
            if len(market_data) > 20:
                sma_short = market_data['close'].tail(5).mean()
                sma_long = market_data['close'].tail(20).mean()
                
                if sma_short > sma_long and market_data['close'].iloc[-2] <= market_data['close'].iloc[-3]:
                    # Golden cross - BUY signal
                    signal = {
                        'symbol': symbol,
                        'type': 'BUY',
                        'position_size': position_size,  # Use configured size
                        'stop_loss': current_price * 0.97,
                        'take_profit': current_price * 1.04,
                        'confidence': 0.6,
                        'volatility': market_data['close'].pct_change().std()
                    }
                    signals.append(signal)
                    
                elif sma_short < sma_long and market_data['close'].iloc[-2] >= market_data['close'].iloc[-3]:
                    # Death cross - SELL signal
                    signal = {
                        'symbol': symbol,
                        'type': 'SELL',
                        'position_size': position_size,  # Use configured size
                        'stop_loss': current_price * 1.03,
                        'take_profit': current_price * 0.96,
                        'confidence': 0.6,
                        'volatility': market_data['close'].pct_change().std()
                    }
                    signals.append(signal)
            
            # Strategy 3: RSI Overbought/Oversold
            if 'rsi' in market_data.columns and not market_data['rsi'].isna().iloc[-1]:
                current_rsi = market_data['rsi'].iloc[-1]
                
                if current_rsi < 30:  # Oversold - BUY signal
                    signal = {
                        'symbol': symbol,
                        'type': 'BUY',
                        'position_size': position_size * 0.8,  # Smaller size for RSI signals
                        'stop_loss': current_price * 0.95,
                        'take_profit': current_price * 1.05,
                        'confidence': 0.5,
                        'volatility': market_data['close'].pct_change().std()
                    }
                    signals.append(signal)
                    
                elif current_rsi > 70:  # Overbought - SELL signal
                    signal = {
                        'symbol': symbol,
                        'type': 'SELL',
                        'position_size': position_size * 0.8,  # Smaller size for RSI signals
                        'stop_loss': current_price * 1.05,
                        'take_profit': current_price * 0.95,
                        'confidence': 0.5,
                        'volatility': market_data['close'].pct_change().std()
                    }
                    signals.append(signal)
            
            logger.info(f"Generated {len(signals)} trading signals for {symbol}")
            return signals
            
        except Exception as e:
            logger.error(f"Error generating signals for {symbol}: {e}")
            return []
    
    def _calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate technical indicators"""
        try:
            # Simple Moving Averages
            df['sma_5'] = df['close'].rolling(window=5).mean()
            df['sma_20'] = df['close'].rolling(window=20).mean()
            
            # RSI (simplified)
            delta = df['close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs = gain / loss
            df['rsi'] = 100 - (100 / (1 + rs))
            
            # Bollinger Bands
            df['bb_middle'] = df['close'].rolling(window=20).mean()
            bb_std = df['close'].rolling(window=20).std()
            df['bb_upper'] = df['bb_middle'] + (bb_std * 2)
            df['bb_lower'] = df['bb_middle'] - (bb_std * 2)
            
            # Additional indicators for better signal generation
            df['price_change_pct'] = df['close'].pct_change()
            df['volume_change_pct'] = df['volume'].pct_change()
            
            return df
        except Exception as e:
            logger.error(f"Error calculating indicators: {e}")
            return df

class RiskManagementAgent:
    def __init__(self):
        # Your existing parameters
        self.max_position_size = 0.1  # 10% of portfolio per trade
        self.max_drawdown = 0.02  # 2% max drawdown per trade
        self.correlation_threshold = 0.7
        
        # Enhanced parameters from my version
        self.max_daily_trades = 10
        self.trade_count_today = 0
        self.last_trade_date = None
        
    def validate_trade(self, trade: Dict, portfolio_value: float, open_positions: List) -> Dict:
        """Validate trade against risk parameters - PRESERVES CONFIGURED POSITION SIZES"""
        try:
            # Get the requested position size from the trade signal
            requested_size = trade.get('position_size', 0.01)
            
            # Calculate maximum allowed position size based on portfolio percentage
            max_allowed_size = portfolio_value * self.max_position_size
            
            # Use the smaller of requested size and max allowed size
            # This preserves the configured position sizes while respecting risk limits
            position_size = min(requested_size, max_allowed_size)
            
            trade['position_size'] = position_size
            
            # Risk scoring (0-1, lower is better)
            risk_score = 0.0
            
            # Your existing risk factors:
            # Position concentration risk
            if len(open_positions) > 2:
                risk_score += 0.2
                
            # Market volatility risk
            if trade.get('volatility', 0) > 0.05:
                risk_score += 0.3
                
            # Enhanced correlation risk check
            correlation_risk = self._check_correlation_risk(trade, open_positions)
            risk_score += correlation_risk
            
            # Additional enhanced risk factors from my version:
            # Confidence-based risk adjustment
            confidence = trade.get('confidence', 0.5)
            risk_score -= (confidence - 0.5) * 0.3  # Higher confidence reduces risk
            
            # Fine-tuned volatility risk
            volatility = trade.get('volatility', 0)
            if volatility > 0.08:  # 8% volatility
                risk_score += 0.1  # Additional risk for high volatility
            elif volatility < 0.01:  # 1% volatility
                risk_score -= 0.1  # Lower risk for low volatility
            
            # Position size risk adjustment
            position_size_ratio = requested_size / (portfolio_value * self.max_position_size)
            if position_size_ratio > 0.8:  # Large position relative to max
                risk_score += 0.2
            elif position_size_ratio < 0.2:  # Small position relative to max
                risk_score -= 0.1
            
            # Ensure risk score is between 0 and 1
            risk_score = max(0.0, min(1.0, risk_score))
            
            # Add approval flag for clarity
            trade['risk_score'] = risk_score
            trade['approved'] = risk_score < 0.7  # Only approve good risk scores
            
            position_size_pct = trade['position_size'] * 100
            logger.info(f"Trade validation - Risk score: {risk_score:.2f}, "
                       f"Position size: {position_size_pct:.1f}%, Approved: {trade['approved']}")
            
            return trade
            
        except Exception as e:
            logger.error(f"Error validating trade: {e}")
            trade['risk_score'] = 1.0  # Maximum risk on error
            trade['approved'] = False
            return trade
    
    def _check_correlation_risk(self, new_trade: Dict, open_positions: List) -> float:
        """Enhanced correlation risk check - FUSED VERSION"""
        try:
            if not open_positions:
                return 0.0
                
            # Count positions in same direction (your logic enhanced)
            same_direction_positions = sum(
                1 for position in open_positions 
                if position.get('type') == new_trade.get('type')
            )
            
            # Enhanced correlation scoring
            if same_direction_positions >= 2:
                return 0.3  # High correlation risk
            elif same_direction_positions >= 1:
                return 0.15  # Medium correlation risk
            else:
                return 0.0  # Low correlation risk
                
        except Exception as e:
            logger.error(f"Error checking correlation risk: {e}")
            return 0.1  # Default medium risk on error
    
    def check_daily_loss_limit(self, current_balance: float, initial_balance: float, loss_limit: float = 0.05):
        """Check daily loss limits - ENHANCED VERSION"""
        try:
            daily_loss = (initial_balance - current_balance) / initial_balance
            
            if daily_loss >= loss_limit:
                return {
                    'halt': True,
                    'reason': f'Daily loss limit of {loss_limit:.1%} reached. Current loss: {daily_loss:.2%}'
                }
            
            # Additional warning at 80% of loss limit
            elif daily_loss >= loss_limit * 0.8:
                logger.warning(f"Approaching daily loss limit: {daily_loss:.2%} (limit: {loss_limit:.1%})")
                return None
            
            return None
            
        except Exception as e:
            logger.error(f"Error checking daily loss limit: {e}")
            return None
    
    def check_correlation_risk(self, trade: Dict, open_positions: List) -> float:
        """Your original method maintained for compatibility"""
        return self._check_correlation_risk(trade, open_positions)
    
    def reset_daily_counts(self):
        """Reset daily trade counts (call this at start of each day)"""
        self.trade_count_today = 0

# For backward compatibility and easy imports
def get_market_analysis_agent():
    return MarketAnalysisAgent()

def get_risk_management_agent():
    return RiskManagementAgent()

# Alternative simple signal generator for testing
class SimpleMarketAnalysisAgent:
    """Simplified version for testing - generates basic signals"""
    def generate_signals(self, market_data: pd.DataFrame, volume_data: pd.Series, 
                        timeframe: str, position_sizes: dict = None) -> List[Dict]:
        """Generate simple trading signals for testing with position sizing"""
        signals = []
        
        if market_data.empty:
            return signals
            
        current_price = market_data['close'].iloc[-1]
        symbol = market_data['symbol'].iloc[0] if 'symbol' in market_data.columns else 'BTC/USDT:USDT'
        
        # Use configured position sizes if available
        default_size = 0.01
        if position_sizes and symbol in position_sizes:
            position_size = position_sizes[symbol]
        else:
            position_size = default_size
        
        # Simple price momentum strategy
        if len(market_data) > 1:
            price_change = (current_price - market_data['close'].iloc[-2]) / market_data['close'].iloc[-2]
            
            if abs(price_change) > 0.01:  # 1% change
                signal_type = 'BUY' if price_change > 0 else 'SELL'
                
                if signal_type == 'BUY':
                    stop_loss = current_price * 0.98
                    take_profit = current_price * 1.03
                else:
                    stop_loss = current_price * 1.02
                    take_profit = current_price * 0.97
                    
                signal = {
                    'symbol': symbol,
                    'type': signal_type,
                    'position_size': position_size,  # Use configured size
                    'stop_loss': stop_loss,
                    'take_profit': take_profit,
                    'confidence': min(0.8, abs(price_change) * 10),
                    'volatility': abs(price_change)
                }
                signals.append(signal)
            
        return signals