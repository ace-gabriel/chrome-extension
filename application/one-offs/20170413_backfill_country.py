import sys, getopt
from os import path

level = 2
parent_dir = path.dirname(path.dirname(path.abspath(__file__)))
for i in xrange(level):
  sys.path.append(parent_dir)
  parent_dir = path.dirname(parent_dir)

from models import User, Phone
from index import db

def backFillUser(dryRun=True):
  print "Is dry run: {}".format(dryRun)
  users = User.query.filter_by(country=None)
  for user in users:
    print "backfilling user {}".format(user.id)
    user.country = "86"
  if not dryRun:
    db.session.commit()
    print "backfilling commited"
  print "backfilling done"

def backFillPhone(dryRun=True):
  phones = Phone.query.filter_by(country=None)
  print "Is dry run: {}".format(dryRun)
  for phone in phones:
    print "backfilling phone {}".format(phone.id)
    phone.country = "86"
  if not dryRun:
    db.session.commit()
    print "backfilling commited"
  print "backfilling done"

def main(argv):
  dryRun = True
  try:
    opts, args = getopt.getopt(argv,"d",["dryRun="])
  except getopt.GetoptError:
    print 'backfill.py -d <dryRun> '
    sys.exit(2)
  for opt, arg in opts:
    if opt in ('-d', '--dryRun'):
      dryRun = arg.lower() in ['true', 'y', 'yes']

  backFillUser(dryRun)
  backFillPhone(dryRun)


if __name__ == "__main__":
  main(sys.argv[1:])
