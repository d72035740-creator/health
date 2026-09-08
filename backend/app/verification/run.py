from app.verification.service import verification_service


def main():
 report=verification_service.run(write_reports=True)
 print(f'{report.overall_status.value}: {report.passed}/{report.total_checks} passed, {report.failed} failed, {report.warnings} warnings')
 raise SystemExit(1 if report.overall_status.value=='NOT_READY' else 0)


if __name__=='__main__':main()
