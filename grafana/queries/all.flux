from(bucket: "my-bucket")
    |> range(start: -100y)
    |> limit(n: 10000000)