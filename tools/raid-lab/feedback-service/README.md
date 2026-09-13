# Private Google Drive feedback inbox

This is a one-time setup for the Raid Lab maintainer. Players do not need Google accounts or folder access. No CAPTCHA or daily upload cap is used.

## Activate uploads

1. Keep the destination folder's **General access → Restricted**. Remove other people if you want only yourself to see feedback. Do not share edit access with players.
2. Open [Google Apps Script](https://script.google.com/home/start), create a project named **Raid Lab feedback**, and replace `Code.gs` with the contents of [Code.gs](Code.gs).
3. Under **Project Settings → Script properties**, add `FEEDBACK_FOLDER_ID`. Its value is the part after `/folders/` in your Drive link. Keep it here; do not put it in the public app configuration.
4. Select and run **checkInbox** in the editor. Authorize your own script to access Drive. This checks the folder without uploading feedback.
5. Choose **Deploy → New deployment → Web app**. Set **Execute as: Me**, **Who has access: Anyone**, and deploy. The upload endpoint is public; the Drive folder remains private. Copy the `/exec` URL.
6. Set `endpoint` in `tools/raid-lab/web/feedback-config.json` to that URL and publish the updated app. For local testing, use `tools/raid-lab/private/feedback-config.json` instead. Never include Google credentials or Script Properties in GitHub.
7. Restart Raid Lab, open a recommendation, and select **Give feedback**. Submit a deliberate test and verify that its ZIP appears in your restricted folder before announcing availability.

When updating the service code, use **Deploy → Manage deployments → Edit → New version** to keep the same URL.

## Email notifications

Replace the existing project's code with the latest `Code.gs`, save, and run **enableEmailNotifications** from the editor. Authorize the additional send-email permission. This sends a setup email to the signed-in script owner's address and saves that address in Script Properties. Then update the **existing** deployment via **Deploy → Manage deployments → Edit → Version: New version → Deploy**. The endpoint URL stays unchanged.

Each new ZIP triggers one email containing the boss, mode, squad and a private Drive link. Submissions cannot choose the recipient. Retries of an already stored receipt do not send another email. If Google rejects an email (for example because of its mail quota), the feedback remains saved; the failure is logged under Apps Script Executions, and email is not automatically retried. Existing feedback is not emailed retroactively.

## What is stored

Each accepted submission creates one `feedback-<receipt>.zip` with `Read me.txt`, `feedback.json`, and one PNG/JPEG image. The JSON contains the message, profile link, selected squad, all squads in that recommendation, builds, encounter settings, available damage accounting and owned-unit snapshot. Older recommendations explicitly label ownership as the current roster when no original snapshot exists. Players review these details before sending. No login session is read or transmitted.

There are no endpoints for listing, reading, editing or deleting submissions. Folder selection happens only in the service configuration. Identical submission IDs return the existing receipt, so retries do not create duplicates. Images have a 2 MB limit and basic signature checks; these are not proof of genuine Battle Records. Treat uploaded files and all text as untrusted user content. Without CAPTCHA or submission caps, deliberate spam can consume Drive storage and Apps Script quotas. Disable the deployment to stop intake.

Google authorization and deployment must be completed by the account owner; copying a folder link cannot grant the app write access.

References: [Apps Script web apps](https://developers.google.com/apps-script/guides/web), [Script properties](https://developers.google.com/apps-script/guides/properties).
