# Event handler: Email

This event handler generates and sends an e-mail message in response to events. 

HTML email is supported if the event contains a mako template 


from events and sends them to  writes all audit records as CSV rows in a CSV file.

This is the event handler that gets used in the stack when using the --csv options on any CLI. 

## Configuration parameters

The following configuration parameters affect the behavior of this event handler.

| Key                 | Description                    | Type    | Default value     |
|---------------------|--------------------------------|---------|-------------------|
| email.smtp_server   | SMTP Server                    | String  | 'giganode1'       |
| email.from          | Value of the Email From: Field | Email   | admin@nowhere.com |
| email.to            | Value of the Email To: Field   | Email   | nobody            |
| email.html          | Send HTML formatted email      | Boolean | True              |

## Usage

### ::: Correlator.Event.csv_writer.CSVListener
    options:
        show_source: false
        show_root_heading: true
