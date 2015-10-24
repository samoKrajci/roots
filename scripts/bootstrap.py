# Bootstraps the Roots instance with the default
# set of the necessary objects

import datetime

site = Site.objects.get_current()

# Create the admin user
admin = User.objects.create(
    username="rootsadmin",
    email="rootsadmin@example.com"
)

# Verify his email
email = admin.emailaddress_set.get(pk=1)
email.verified = True
email.save()

season = Season(
    competition=competition,
    name="First season",
    year=datetime.date.today().year,
    number=1,
    start=datetime.datetime.now(),
    end=datetime.datetime.now()+datetime.timedelta(days=30),
)
season.save()

problemset_series_1 = ProblemSet(
    name="Problems in the first series",
    competition=competition
)
problemset_series_1.save()

series = Series(
   season=season,
   name="First series",
   number=1,
   submission_deadline=datetime.datetime.now()+datetime.timedelta(days=30),
   problemset=problemset_series_1
)
series.save()
