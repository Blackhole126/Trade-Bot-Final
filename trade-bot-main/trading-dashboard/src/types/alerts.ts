// ==================== LEGACY ALERT TYPES (Backward Compatible) ====================

// Alert Types
export interface PriceAlert {
  id: string;
  symbol: string;
  type: 'above' | 'below' | 'change';
  targetPrice?: number;
  changePercent?: number;
  isActive: boolean;
  createdAt: Date;
  triggeredAt?: Date;
  notificationSent: boolean;
}

export interface PredictionAlert {
  id: string;
  symbol: string;
  action: 'LONG' | 'SHORT' | 'HOLD';
  previousAction?: 'LONG' | 'SHORT' | 'HOLD';
  isActive: boolean;
  createdAt: Date;
  triggeredAt?: Date;
}

// AppNotification - renamed to avoid conflict with browser Notification API
export interface AppNotification {
  id: string;
  type: 'price' | 'prediction' | 'stop-loss' | 'system';
  title: string;
  message: string;
  symbol?: string;
  timestamp: Date;
  read: boolean;
  actionUrl?: string;
}

export type LegacyAlertType = PriceAlert | PredictionAlert;

// ==================== NEW ENHANCED ALERT SYSTEM ====================

export type NewAlertType = 
  | 'price_above' 
  | 'price_below' 
  | 'prediction_buy' 
  | 'prediction_sell' 
  | 'confidence_high' 
  | 'volume_surge' 
  | 'gain_loss';

export type NotificationChannel = 'browser' | 'email' | 'webhook';

export interface Alert {
  id: string;
  symbol: string;
  alert_type: NewAlertType;
  value?: number;
  enabled: boolean;
  notification_channels: NotificationChannel[];
  description?: string;
  created_at: string;
  last_triggered?: string;
  trigger_count: number;
}

export interface AlertCreateRequest {
  symbol: string;
  alert_type: NewAlertType;
  value?: number;
  enabled?: boolean;
  notification_channels?: NotificationChannel[];
  description?: string;
}

export interface AlertUpdateRequest {
  alert_type?: NewAlertType;
  value?: number;
  enabled?: boolean;
  notification_channels?: NotificationChannel[];
  description?: string;
}

export interface AlertCheckResponse {
  alert_id: string;
  symbol: string;
  alert_type: NewAlertType;
  should_trigger: boolean;
  current_value: number;
  threshold_value: number;
  message: string;
  notification_channels: NotificationChannel[];
}

export interface TriggeredAlert {
  alert_id: string;
  symbol: string;
  alert_type: NewAlertType;
  should_trigger: boolean;
  current_value: number;
  threshold_value: number;
  message: string;
  notification_channels: NotificationChannel[];
}

export const ALERT_TYPE_LABELS: Record<NewAlertType, string> = {
  price_above: '📈 Price Above',
  price_below: '📉 Price Below',
  prediction_buy: '🟢 Buy Signal',
  prediction_sell: '🔴 Sell Signal',
  confidence_high: '⭐ High Confidence',
  volume_surge: '📊 Volume Surge',
  gain_loss: '💰 Portfolio Gain/Loss'
};

export const ALERT_TYPE_DESCRIPTIONS: Record<NewAlertType, string> = {
  price_above: 'Alert when price crosses above a specific level (₹)',
  price_below: 'Alert when price crosses below a specific level (₹)',
  prediction_buy: 'Alert when ML model predicts BUY signal',
  prediction_sell: 'Alert when ML model predicts SELL signal',
  confidence_high: 'Alert when prediction confidence exceeds threshold (%)',
  volume_surge: 'Alert when trading volume spikes significantly',
  gain_loss: 'Alert when portfolio gain/loss reaches percentage (%)'
};





