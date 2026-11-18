from django.core.management.base import BaseCommand

from sensing.models import Device, Report
from sensing.trust import score_cell


class Command(BaseCommand):
    help = "Fires three demo scenarios into the database and prints the trust engine's verdict."

    def show(self, cell_id):
        r = score_cell(cell_id)
        self.stdout.write(
            f"   cell {r['cell_id']}: {r['reports']} report(s), "
            f"{r['independent_sources']} independent source(s) -> "
            f"trust score {r['score']} -> {r['state'].upper()}"
        )

    def handle(self, *args, **options):
        # Clear old demo data so the command can be run again and again
        Device.objects.filter(device_id__startswith="demo-").delete()

        self.stdout.write("\n1) Real pothole: 5 independent phones in the same spot")
        for i in range(1, 6):
            d = Device.objects.create(device_id=f"demo-real-{i}", fingerprint=f"demo-fp-{i}", reliability=0.8)
            Report.objects.create(device=d, latitude=-0.6817, longitude=34.7666, magnitude=15 + i)
        self.show(Report.make_cell_id(-0.6817, 34.7666))

        self.stdout.write("\n2) One fake report from a single phone")
        d = Device.objects.create(device_id="demo-faker", fingerprint="demo-fp-faker", reliability=0.4)
        Report.objects.create(device=d, latitude=-0.6917, longitude=34.7766, magnitude=31)
        self.show(Report.make_cell_id(-0.6917, 34.7766))

        self.stdout.write("\n3) Bot swarm: 6 cloned devices sharing one fingerprint")
        for i in range(1, 7):
            d = Device.objects.create(device_id=f"demo-bot-{i}", fingerprint="demo-clone", reliability=0.4)
            Report.objects.create(device=d, latitude=-0.6717, longitude=34.7566, magnitude=22)
        self.show(Report.make_cell_id(-0.6717, 34.7566))

        self.stdout.write("\nDone. Open /admin to see the demo devices and reports.\n")