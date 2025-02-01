// v.bucket, v.timeRangeStart, and v.timeRange stop are all variables supported by the flux plugin and influxdb
from(bucket: v.bucket)
    |> range(start: v.timeRangeStart, stop: v.timeRangeStop)
    |> filter(fn: (r) => r._measurement == "air_quality")
    |> filter(fn: (r) => r._field == "aqi")
    |> group(columns: [])
    |> aggregateWindow(every: v.windowPeriod, fn: mean, createEmpty: false)