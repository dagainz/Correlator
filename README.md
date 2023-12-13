# Welcome to the Correlator repository!

Correlator is a log processing system written in Python. 

It consumes and processes log data looking for patterns, and taking specific actions when they occur. It provides an
interface to write both custom detection and/or action logic in python, which it can dynamically import.

out-of-the-box functionality includes:

- RFC 5424 compliant TCP syslog server processes syslog records received from a remote system. It also has the
ability to capture received syslog packets to a file, and to use these capture files as input.
- An OpenSSH *logic module*: Detection logic that looks for patterns, such as **Successful login** in OpenSSH's
log stream, and dispatch *events* in response.
- Several *event handlers*: action logic that take action when these events occur.
  - Email: Generates an email from a template using mako, and send via SMTP.
  - CSV: Writes event data to rows in a csv file.
  - SMS: Sends a basic SMS via twilio.

And more!

---

### Documentation and resources

mkdocs based Markdown formatted documentation is provided in /doc.

A pre-rendered HTML format version is hosted on GitHub pages:
- [https://tim-pushor.github.io/Correlator/](https://tim-pushor.github.io/Correlator/) - Documentation index
- [https://tim-pushor.github.io/Correlator/quickstart/](https://tim-pushor.github.io/Correlator/quickstart/) - Quick
start

# Credits

Developer - Tim Pushor

# License

MIT License

Copyright (c) 2023 Tim Pushor

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
