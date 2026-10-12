# StockTradingSignals - Automatic Scheduling

This document explains how the application is automatically scheduled to run during stock trading hours.

## Schedule Overview

The application runs **Monday-Friday** during and after US stock trading hours:

| Time | Action | Purpose |
|------|--------|---------|
| 8:00 AM CT (9:00 AM ET) | **START** | Begin listening 30 min before market opens |
| 8:00 AM - 7:00 PM CT | **ACTIVE** | Scrape Discord/Messenger, forward signals, queue posts |
| 7:00 PM CT (8:00 PM ET) | **STOP** | Stop application after 4 hours post-market close |

### Why This Schedule?

- **9:00 AM ET**: 30 minutes before market opens → Start scraping and forwarding signals
- **4:00 PM ET**: US stock market closes → Continue running for 4 more hours
- **8:00 PM ET**: Stop to avoid off-hours scraping (market reopens next day)

## Cron Jobs Configuration

Two cron jobs manage the automatic start and stop:

```bash
# Start at 9:00 AM ET (8:00 AM CT) - 30 min before market opens, Monday-Friday
0 8 * * 1-5 /home/bear2927/StockTradingSignals/scripts/start_app.sh

# Stop at 8:00 PM ET (7:00 PM CT), Monday-Friday
0 19 * * 1-5 /home/bear2927/StockTradingSignals/scripts/stop_app.sh
```

## Managing the Schedule

### View Current Cron Jobs
```bash
crontab -l
```

### Disable Scheduling (Keep app running manually)
```bash
crontab -e
# Comment out the two lines starting with #

# Or remove all:
crontab -r
```

### Re-enable Scheduling
```bash
/home/bear2927/StockTradingSignals/scripts/setup_cron.sh
```

### Manual Control

**Start application immediately:**
```bash
/home/bear2927/StockTradingSignals/scripts/start_app.sh
```

**Stop application immediately:**
```bash
/home/bear2927/StockTradingSignals/scripts/stop_app.sh
```

**Check if app is running:**
```bash
ps aux | grep -E "python -m src.main|node src/messenger/scraper" | grep -v grep
```

## Logs

Scheduling logs are stored in `/var/log/stock-trading-signals/`:

- **scheduler.log** - Start/stop events and timestamps
- **app.log** - Python application logs
- **scraper.log** - Node.js scraper logs

**View scheduler logs:**
```bash
tail -f /var/log/stock-trading-signals/scheduler.log
```

## Timezone Notes

- **System timezone**: America/Chicago (CDT/CST)
- **Stock trading timezone**: America/New_York (EDT/EST)
- **Offset**: ET is 1 hour ahead of CT
- **Cron times**: Adjusted to system timezone (8:30 AM CT = 9:30 AM ET)

If your system timezone is different, adjust cron times accordingly:
- Add 1 hour for CST/CDT systems
- Adjust as needed for other timezones

## Troubleshooting

### Application not starting at scheduled time

1. **Check if cron daemon is running:**
   ```bash
   sudo systemctl status cron
   ```

2. **Verify cron jobs are configured:**
   ```bash
   crontab -l
   ```

3. **Check scheduler logs:**
   ```bash
   tail -50 /var/log/stock-trading-signals/scheduler.log
   ```

4. **Test the start script manually:**
   ```bash
   /home/bear2927/StockTradingSignals/scripts/start_app.sh
   ```

### Application won't stop

The stop script uses `pkill` to gracefully terminate processes. If processes don't stop:

```bash
# Force kill if needed (not recommended)
pkill -9 -f "python -m src.main"
pkill -9 -f "node src/messenger/scraper.js"
```

### Permissions errors

The scripts need permission to write logs to `/var/log/stock-trading-signals/`. If you see permission errors:

```bash
sudo mkdir -p /var/log/stock-trading-signals
sudo chown $USER:$USER /var/log/stock-trading-signals
```

## Testing the Schedule

To test the cron jobs without waiting for actual market hours:

```bash
# Edit crontab to run in 1 minute
crontab -e

# Change the time to 1 minute from now, save and exit
# Watch the logs
tail -f /var/log/stock-trading-signals/scheduler.log

# After testing, restore original times
/home/bear2927/StockTradingSignals/scripts/setup_cron.sh
```

## Advanced: Custom Schedule

To modify the schedule (e.g., different hours or days):

1. Edit `/home/bear2927/StockTradingSignals/scripts/start_app.sh` - change start conditions
2. Edit `/home/bear2927/StockTradingSignals/scripts/stop_app.sh` - change stop conditions
3. Edit crontab: `crontab -e` - modify times and days

**Common cron patterns:**
- `0 9 * * 1-5` - 9:00 AM, Monday-Friday
- `0 17 * * *` - 5:00 PM, every day
- `0 8-17 * * 1-5` - Every hour from 8 AM to 5 PM, Mon-Fri
- `*/15 9-16 * * 1-5` - Every 15 minutes from 9 AM to 4 PM, Mon-Fri
