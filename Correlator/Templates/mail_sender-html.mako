<%def name="subject()">
    % if event.severity_name in ('Error', 'Warning'):
        ${event.severity_name}: ${event.summary}
    % else:
        ${event.summary}
    % endif
</%def>\
<%
    sevname = event.severity_name
    sevclass = sevname.lower()
%>\
MIME-Version: 1.0
Content-Type: multipart/alternative;
 boundary="===============8356729966348928787=="
Subject: ${Subject}
From: ${From}
To: ${To}

--===============8356729966348928787==
Content-Type: text/plain; charset="utf-8"
Content-Transfer-Encoding: 7bit

This e-mail message requires an HTML capable mail reader

--===============8356729966348928787==
MIME-Version: 1.0
Content-Type: multipart/related;
 boundary="===============6372767452273732307=="

--===============6372767452273732307==
Content-Type: text/html; charset="utf-8"
Content-Transfer-Encoding: quoted-printable

<!DOCTYPE html>
<html lang=3D"en" xmlns=3D"http://www.w3.org/1999/xhtml" xmlns:o=3D"urn:schem=
as-microsoft-com:office:office">
 <head>
  <meta charset=3D"utf-8"/>
  <meta content=3D"width=3Ddevice-width,initial-scale=3D1" name=3D"viewport"/>
  <meta name=3D"x-apple-disable-message-reformatting"/>
  <title>
  </title>
  <!--[if mso]>
    <noscript>
        <xml>
            <o:OfficeDocumentSettings>
                <o:PixelsPerInch>96</o:PixelsPerInch>
            </o:OfficeDocumentSettings>
        </xml>
    </noscript>
    <![endif]-->
  <style>
   table, td, div, h1, p {
            font-family: Arial, sans-serif;
        }

        a:link, a:visited {
            color: black;
            text-decoration: none;
        }

        a:hover {
            color: blue;
            text-decoration: underline;
        }

        .informational {
            color: green;
            font-weight: bold;
        }

        .warning {
            color: yellow;
            font-weight: bold;
        }

        .error {
            color: red;
            font-weight: bold;
        }

        table.datatable {
            border: 0px none;
            border-collapse: collapse;
            padding: 5px;
        }

        table.datatable td {
            border: 0px none;
        }

        table.datatable th {
            padding: 5px;
            background: #f0f0f0;
            color: #313030;
        }

        table.datatable td:first-child {
            text-align: right;
            padding: 5px;
            background: #ffffff;
            color: #313030;
            font-weight: normal;
        }

        table.datatable td {
            text-align: left;
            font-weight: bold;
            padding: 10px;
            background: #ffffff;
            color: #313030;
        }
  </style>
 </head>
 <body style=3D"margin:0;padding:0;">
  <table role=3D"presentation" style=3D"width:100%;border-collapse:collapse;b=
order:0;border-spacing:0;background:#ffffff;">
   <tr>
    <td align=3D"center" style=3D"padding:0;">
     <table role=3D"presentation" style=3D"width:602px;border-collapse:collap=
se;border:1px solid #cccccc;border-spacing:0;text-align:left;">
      <tr>
       <td style=3D"padding:0;">
        <table role=3D"presentation" style=3D"width:602px;border-collapse:col=
lapse;border:1px solid #cccccc;border-spacing:0;text-align:left;">
         <tr>
          <td align=3D"center" style=3D"padding:36px 30px 42px 30px;backgroun=
d:#70bbd9; width: 100%;">
           <div style=3D"width: 80%; margin: auto;">
            <div style=3D"display:flex; align-items: center;">
             <img alt=3D"" src=3D"cid:169281747858.65136.6710641930104898386@=
1.0.0.127.in-addr.arpa" style=3D"height:auto;display:block;float: left" width=
=3D"50"/>
             <span style=3D"padding-left: 20px; font-size: 150%">
              You have a new notification.
             </span>
            </div>
           </div>
          </td>
         </tr>
         <tr>
          <td style=3D"padding:36px 30px 42px 30px">
           <p>
            The following message is of severity
            <span class=3D"${sevclass}">
             ${sevname}
            </span>
            :
           </p>
           <div style=3D"width:80%; margin: auto; font-size: 115%; margin-top=
: 40px;">
            ${summary}
            </div>
           <p style=3D"margin-top: 40px;">
            The attributes of the event that generated this
                                        notification are:
           </p>
${data_table}
           <div style=3D"width: 100%; margin-top: 50px; text-align: center; f=
ont-style: italic; font-size: 90%">
            Please do not respond to this e-mail as this mailbox is not monit=
ored
           </div>
          </td>
         </tr>
         <tr>
          <td style=3D"padding:36px 30px 42px 30px;;background:#909090;font-s=
ize: 80%; color: white">
           <p>
            This notification was created by Correlator, the Open Source log =
processing
                                        system written in Python. For more in=
formation about Correlator,
            <a href=3D"https://github.com/tim-pushor/Correlator">
             visit the repository on
                                            GitHub.
            </a>
           </p>
          </td>
         </tr>
        </table>
       </td>
      </tr>
     </table>
    </td>
   </tr>
  </table>
 </body>
</html>

--===============6372767452273732307==
Content-Type: image/png
Content-Transfer-Encoding: base64
Content-ID: 169281747858.65136.6710641930104898386@1.0.0.127.in-addr.arpa
MIME-Version: 1.0
Content-Disposition: inline

iVBORw0KGgoAAAANSUhEUgAAADYAAAA7CAIAAAC/ue5UAAAAAXNSR0IArs4c6QAAAMZlWElmTU0A
KgAAAAgABgESAAMAAAABAAEAAAEaAAUAAAABAAAAVgEbAAUAAAABAAAAXgEoAAMAAAABAAIAAAEx
AAIAAAAVAAAAZodpAAQAAAABAAAAfAAAAAAAAABIAAAAAQAAAEgAAAABUGl4ZWxtYXRvciBQcm8g
Mi4zLjMAAAAEkAQAAgAAABQAAACyoAEAAwAAAAEAAQAAoAIABAAAAAEAAAA2oAMABAAAAAEAAAA7
AAAAADIwMjM6MDg6MjIgMTY6MjM6MDcAzBrsaAAAAAlwSFlzAAALEwAACxMBAJqcGAAAA7BpVFh0
WE1MOmNvbS5hZG9iZS54bXAAAAAAADx4OnhtcG1ldGEgeG1sbnM6eD0iYWRvYmU6bnM6bWV0YS8i
IHg6eG1wdGs9IlhNUCBDb3JlIDYuMC4wIj4KICAgPHJkZjpSREYgeG1sbnM6cmRmPSJodHRwOi8v
d3d3LnczLm9yZy8xOTk5LzAyLzIyLXJkZi1zeW50YXgtbnMjIj4KICAgICAgPHJkZjpEZXNjcmlw
dGlvbiByZGY6YWJvdXQ9IiIKICAgICAgICAgICAgeG1sbnM6dGlmZj0iaHR0cDovL25zLmFkb2Jl
LmNvbS90aWZmLzEuMC8iCiAgICAgICAgICAgIHhtbG5zOmV4aWY9Imh0dHA6Ly9ucy5hZG9iZS5j
b20vZXhpZi8xLjAvIgogICAgICAgICAgICB4bWxuczp4bXA9Imh0dHA6Ly9ucy5hZG9iZS5jb20v
eGFwLzEuMC8iPgogICAgICAgICA8dGlmZjpZUmVzb2x1dGlvbj43MjAwMDAvMTAwMDA8L3RpZmY6
WVJlc29sdXRpb24+CiAgICAgICAgIDx0aWZmOlhSZXNvbHV0aW9uPjcyMDAwMC8xMDAwMDwvdGlm
ZjpYUmVzb2x1dGlvbj4KICAgICAgICAgPHRpZmY6UmVzb2x1dGlvblVuaXQ+MjwvdGlmZjpSZXNv
bHV0aW9uVW5pdD4KICAgICAgICAgPHRpZmY6T3JpZW50YXRpb24+MTwvdGlmZjpPcmllbnRhdGlv
bj4KICAgICAgICAgPGV4aWY6UGl4ZWxZRGltZW5zaW9uPjU5PC9leGlmOlBpeGVsWURpbWVuc2lv
bj4KICAgICAgICAgPGV4aWY6UGl4ZWxYRGltZW5zaW9uPjU0PC9leGlmOlBpeGVsWERpbWVuc2lv
bj4KICAgICAgICAgPHhtcDpNZXRhZGF0YURhdGU+MjAyMy0wOC0yMlQxNjoyMzo1OS0wNjowMDwv
eG1wOk1ldGFkYXRhRGF0ZT4KICAgICAgICAgPHhtcDpDcmVhdGVEYXRlPjIwMjMtMDgtMjJUMTY6
MjM6MDctMDY6MDA8L3htcDpDcmVhdGVEYXRlPgogICAgICAgICA8eG1wOkNyZWF0b3JUb29sPlBp
eGVsbWF0b3IgUHJvIDIuMy4zPC94bXA6Q3JlYXRvclRvb2w+CiAgICAgIDwvcmRmOkRlc2NyaXB0
aW9uPgogICA8L3JkZjpSREY+CjwveDp4bXBtZXRhPgongOcBAAAHYUlEQVRoBe1ZWVBTVxjOvdmR
LQjIvhhF1LSISgW30o5OW3WcMm1nOk6n0+lLn5zp9K2PbR/60D7qdJxO2+mKVjtqLdWqVAoqZVM2
iWxBCBCSkIXATXKTe+/pn4Ws915yAZfOcB7gnP/8y3f+/5w//z0H+/DGkOjZbvizDc+HTrISiIhh
LGMD2oZzSCQqrTmUv2s/jou5FSKcYZKcjhz9yIbx4TSLQeylKLnCnFsyXVpuyS3ySuQMzuKyFUG0
Twxf//Qk5XYBLPNA9w5iXl17jBUiztAqq2lTf2t5Z3OK1SQSwaL8DYnUvf/SYrGloPRB9eFHmyuI
pBQRFgV0RRAfXjuHvF4Mw8Ca0z473dfOClFCU8Vj2ormy3kjA35wwO8T8TX/fzHDZE+MqIyTuZV7
e6pftWTmMRHRWBFEl82K0KI/Aibj/uKIAXw1f3yfbpwS+RazCC6WE5OS5Jb2Jhnp7nixzpyVF/Jl
lEtjpbjHDE2RC3avL8RhiDRJkg4boqhIuXSrcWfj+UV8kTMsfYxBxT1tz3fcWOdaCE2Lq989GRos
2YHzQc5ZTUO9k+3N+s5/TA+7KdIdkmK8HsJitOt1FOmUKJIkciXsgQN//VI8cN/vvyAjJpPhKcm4
Kl2SuR4xtIj0hDRAB0cozWxwZOVbsguQfwslGmgIKOmwTt1vNfR1AAiHcZKOABewsWA2DN28hMvk
qdn5RS8c3Hr0RB4xt7HrTiQCEULrDuxP2rsPUGIyqe3Hn9ydXZELAGaZ27mto3F0605SpoRhQhAZ
SC7DvZBcZnVap8XEv/8YD2nTjxZVHcBwceWdqxLaG4MAUTTjcsm2a6QlxZKGq1ELCA6wrIlhlXl6
Jl+dGESa1t26MtBQP2+aYmiaTSMLLWPjVolckTOmjcEHp8XV2eEe6MtQKiWFRSySfhKkzLxRbUIQ
Ye/3XPx28NoFDzHPpY6VLpUrAJzCnzKjGTCGcIoIJ+N2cx5uv8B600RAkDfQNNV38TvtlXrKEz4T
0fY4R7DTfdkFMZwc/BMY5KCgUU6ICDGjTQ3aa+eXgS9snSsJhjk4e2jxN4YjLyJkGe7XNtQLjW/I
IKJpSJgUzumCECd7ByGHKiswxQ7RvWDX/nl2bkbPLp8A1WW3QHqfX58NWSYB9jgWDDMWlwWoLBAh
p8z0dszqHkKijhNNiAD7cPzuDc+8/cGewwjnCLbHK3K7IQGxaiTSVQYeiPDLZuhtXzDPsAonSJzq
6yDMhgHNHnt2HpsIcvd0zf92wTupj81KcMYw0dDOg27FuoAgixfn9Drb+MgyA7QIByIw3HiZ8Xq7
a+tIhe9HIrphRFOL5fRpz/BwNN03MhdtGqrYBxVaYCoOIk3bJ0bmDOPxkoIoEGvd7evGB50PNXv6
a49REp5SN0qxPTu3b/8Rm2pDqCaKPXEet5Mwz0QWB1EKhAzguNw7eyY5v7i76rBYhLb9/YeMN79C
fK25RQ/2HdFtrqAk0pCp2EqHdFj0XbdtE6MhjpV04FxbxwZV5RXzZRXujKxku1lJOLD4I44QJZXp
NbvuvfTGI/X2QPUQshvrRa/TSTrsoekVdiDc5sG+llOfVNS956ms0Zduyx0fLO9qUhn0Yg8J1SES
Yx6Fckat0Va9bMnKJZJSI+vtgPVYiBTlXZUoR64NYnLnzOf63Qcq3/7ArqmGKgu+BLBgLezzKSWW
kFJ5qMyOlIV+LEQ4yPy1Vox8QkOEvC5ipPnqSMu1DWUazdETmVt3SJPTcLbvvXiFcRDjWVaJEqgr
TEP9jYMfg8rjX/6cXugrB5dscUlnSYkVMwSwJq7mKUBMHFyAcw2iUI+x8a95kc0rQmlrXhTqMTb+
NS+yeUUobc2LQj3Gxr/mRTavCKX9D73I+KpuUuhCl8EPV7oJfgdHedFpNY7dvTFvnlqGSaEiAw1n
XfbZRKTCVbfLYrxf/9XkvTteJ5GI5Ep4oKodb7vlcRHV73+UlMl6XRFWH/Qi3IC1ffOFT8wZvqoP
cz2GHuyo6e7WllOfOabH+NUHIY40/T7V00bD/niCDS5VzEO993/9mv+DLghxuqcNLg+eILygKUBp
1Q16iDke00GIqTmFPEyPcwqTJaXIFMk8JoLHZcuhusl7re45370lD/fqTmEYrkzP1Bx/B5OET228
CSzwZA432xadFi63XbPGBNNVvC6hFGlK6saDR3K278Z4v/mD8GFBmertmeptEU96Qi0ui9//rsAv
GeNhjP8tBHTBTpjTjxLgbO6mSM9QFW4Sw9PLarQYiEurhB+u8dbG8bs3uVlRQdXBdcdzlE8LIi6W
MhS1YDVxPbZBklOnqKSKJO41CJsJJp3EhXCJJK+yJi2/lEtEmZaRVrhRLI+/3+aSWIIuGCJc8GeV
PVeyp1aenBqvGxagrj2aXb5D6N1SvKoQRfBeBEmxTFH22lvwKN536QeXwxbSpUzPKH/lzbJDr7Oi
D7EJ7QTzolAx4Ie9CBfjE+3NtrFBDMfS8kvyKvcmbyjAxctZNg+A5UPkUbq6U/8BIQMcSoO8v5EA
AAAASUVORK5CYII=

--===============6372767452273732307==--

--===============8356729966348928787==--


