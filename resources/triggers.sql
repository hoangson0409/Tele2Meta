CREATE TRIGGER trigger3
    AFTER INSERT
    ON trade_info_pnl FOR EACH ROW

    UPDATE trade_best_results
    SET best_profit = (select max(pnl) from trade_info_pnl where trade_id = trade_best_results.trade_id);
    
DROP TRIGGER IF EXISTS trigger_for_update;
DELIMITER $$
CREATE TRIGGER trigger_for_update AFTER INSERT ON trade_info_pnl FOR EACH ROW
BEGIN
IF NOT EXISTS (SELECT trade_id FROM trade_best_results WHERE trade_id = NEW.trade_id) THEN
    INSERT INTO trade_best_results (trade_id, best_profit)
    VALUES (NEW.trade_id, (select max(pnl) from trade_info_pnl where trade_id = NEW.trade_id));
END IF;
END $$
DELIMITER ;