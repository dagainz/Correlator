<%def name="body_text()">
Hello there,

I am the Correlator log processing system and unfortunately I have to inform you that there has been a problem. This e-email is the notification that you asked me to provide when this happens. Please do not reply to this e-mail as it will go unanswered.

The details of the problem follow:

${text_detail}

</%def>

<%def name="body_html()">
<!DOCTYPE html>
<html>
<head>
	<title>HTML Table Generator</title>
	<style>
		table.datatable {
			border-style: none;
			border-collapse:collapse;
			padding:10px;
		}
		table.datatable th {
			padding:10px;
			background: #f0f0f0;
			color: #313030;
		}
		table.datatable td:first-child {
			text-align:right;
			padding:10px;
			background: #ffffff;
			color: #313030;
            font-weight: bold;
		}
		table.datatable td {
			text-align:left;
			padding:10px;
			background: #ffffff;
			color: #313030;
		}
	</style>
</head>
<body>

<p>Hello there,</p>
<p>I am the Correlator log processing system and unfortunately I have to inform you that there has been a problem.
This e-email is the notification that you asked me to provide when this happens. Please do not reply to this e-email as
it will go unanswered.</p>

<p>The details of the problem follow:</p>
${html_detail}
</body>
</html>
</%def>

<%def name="subject()">Error: ${summary}</%def>
