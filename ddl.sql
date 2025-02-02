CREATE TABLE air_quality_measurements (
    station_id INTEGER NOT NULL,
    pollutant VARCHAR(10) NOT NULL,
    aqi INTEGER NOT NULL CHECK (aqi >= 0),
    timestamp TIMESTAMPTZ NOT NULL,
    PRIMARY KEY (station_id, pollutant, timestamp)
);

CREATE TABLE stations (
    station_id INTEGER PRIMARY KEY,
    gov_reference_number NUMERIC(10,1) NOT NULL,
    status VARCHAR(10) NOT NULL CHECK (status IN ('open', 'closed')),
    name VARCHAR(255) NOT NULL,
    address VARCHAR(500) NOT NULL,
    city VARCHAR(100) NOT NULL,
    latitude DECIMAL(9,6) NOT NULL,
    longitude DECIMAL(9,6) NOT NULL,
    x_coord DECIMAL(15,9) NOT NULL,
    y_coord DECIMAL(15,9) NOT NULL,
    sector_id INTEGER NOT NULL,
    sector_name VARCHAR(50) NOT NULL,
    height DECIMAL(5,1) CHECK (height >= 0),
    timestamp TIMESTAMPTZ NOT NULL
);

CREATE TABLE violations (
    violation_id SERIAL PRIMARY KEY,
    offender_name TEXT NOT NULL,
    offence TEXT NOT NULL,
    location TEXT NOT NULL,
    infraction_date DATE NOT NULL,
    judgment_date DATE NOT NULL,
    amount_claimed NUMERIC(12,2) CHECK (amount_claimed >= 0),
    sentence NUMERIC(12,2) CHECK (sentence >= 0),
    regulation_violated VARCHAR(20) NOT NULL,
    domain VARCHAR(50) NOT NULL,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT valid_judgment_date CHECK (judgment_date >= infraction_date)
);