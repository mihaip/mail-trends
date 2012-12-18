Mail Trends lets you analyze and visualize your email (as extracted from an IMAP server). You can see:

* Distribution of messages by year, month, day, day of week and time of day
* Distribution of messages by size and your top 40 largest messages
* The top senders, recipients and mailing lists you're on.
* Distributions of senders, recipients and mailing lists over time
* The distribution of thread lengths and the lists and people that result in the longest threads

To see some sample output, here's [the result](http://persistent.info/mail-trends/enron/) of running it over the [Enron Email Dataset](http://www.cs.cmu.edu/~enron/) (just two people's worth of emails).

To run this over your own mail, see the [getting started](https://github.com/mihaip/mail-trends/wiki/Getting-Started) page.

![Screenshot](https://f.cloud.github.com/assets/513813/18310/690f2708-48a9-11e2-8d07-26684df2bcc4.png)

See the [plan](https://github.com/mihaip/mail-trends/wiki/Plan) document for rough ideas of what will be worked on next. If you'd like to help out, you can email me at [mihai at persistent dot info](mailto:mihai at persistent dot info).

Mail Trends depends on the following packages (they are currently all included in its Subversion repository, and thus don't need to be downloaded/installed separately):

* [Python Google Chart](http://pygooglechart.slowchop.com/) for generating chart URLs for Google's [Chart API](http://code.google.com/apis/chart/)
* [jwzthreading](http://www.amk.ca/python/code/jwz) for an implementation of [Jamie Zawinsky's threading algorithm](http://www.jwz.org/doc/threading.html)
* [python-twitter](http://code.google.com/p/python-twitter/) for the `FileCache` class
* [Cheetah](http://www.cheetahtemplate.org/) for HTML templates
* [jQuery](http://jquery.com/) for adding interactivity to the HTML output