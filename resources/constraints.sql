desc trade_info_static;
ALTER TABLE trade_best_results
ADD FOREIGN KEY (trade_id) REFERENCES trade_info_static(trade_id);
ALTER TABLE trade_info_pnl
ADD FOREIGN KEY (trade_id) REFERENCES trade_info_static(trade_id);
