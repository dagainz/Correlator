# Event handler: CSV

This handler writes all audit records as CSV rows in a CSV file.

This is the event handler that gets used in the stack when using the --csv options on any CLI. 

## Configuration parameters

The following configuration parameters affect the behavior of this event handler.

| Key                   | Description                           | Type   | Default value |
|-----------------------|---------------------------------------|--------|---------------|
| csv.output_directory  | The directory to write CSV files into | String | 'csv'         |

## Usage

### ::: Correlator.Event.csv_writer.CSVListener
    options:
        show_source: false
        show_root_heading: true
