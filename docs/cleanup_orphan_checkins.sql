/*
  Clears the half-written stays left behind by a failed POST /checkin.

  Why they exist: POST /checkin commits payment, check-in, guest, attachment,
  checkinguest, log and guestversion in *separate* steps, so a failure part way
  through leaves a check-in row with no guests on it. No endpoint can clean that
  up - POST /checkout on such a row raises "'NoneType' object has no attribute
  'Id'", because the handler assumes the stay has guests.

  These rows are mostly harmless once IsActive is 0: they occupy the window
  between their CheckinDate and CheckoutDate for that room, so a check-in dated
  inside that window is refused with an overlap error. A check-in dated after it
  is accepted normally.

  RUN THE SELECTS FIRST and read what comes back. Only run the DELETEs if every
  row listed is one you expect to lose.
*/

USE [president_hotel];
GO

-- 1. Check-in rows that have no guest on them at all.
SELECT c.Id, c.RoomNumber, c.CheckinDate, c.IsActive, c.PaymentId,
       c.AddedAt, c.AddedFrom
  FROM [itsthe1.id].[checkin] c
 WHERE NOT EXISTS (SELECT 1
                     FROM [itsthe1.id].[checkinguest] g
                    WHERE g.CheckinId = c.Id)
 ORDER BY c.Id;
GO

-- 2. Payment rows that no check-in points at.
SELECT p.Id, p.PaymentTypeId, p.PaidAmount, p.AddedAt
  FROM [itsthe1.id].[payment] p
 WHERE NOT EXISTS (SELECT 1
                     FROM [itsthe1.id].[checkin] c
                    WHERE c.PaymentId = p.Id)
 ORDER BY p.Id;
GO

/*
  ---------------------------------------------------------------------------
  Everything below deletes. Nothing above this line changes the database.
  ---------------------------------------------------------------------------
*/

-- BEGIN TRANSACTION;

-- -- Rows that reference the orphan check-ins have to go first.
-- DELETE FROM [itsthe1.id].[checkout]
--  WHERE CheckinId IN (SELECT c.Id
--                        FROM [itsthe1.id].[checkin] c
--                       WHERE NOT EXISTS (SELECT 1
--                                           FROM [itsthe1.id].[checkinguest] g
--                                          WHERE g.CheckinId = c.Id));

-- DELETE FROM [itsthe1.id].[log]
--  WHERE CheckinId IN (SELECT c.Id
--                        FROM [itsthe1.id].[checkin] c
--                       WHERE NOT EXISTS (SELECT 1
--                                           FROM [itsthe1.id].[checkinguest] g
--                                          WHERE g.CheckinId = c.Id));

-- DELETE FROM [itsthe1.id].[checkin]
--  WHERE NOT EXISTS (SELECT 1
--                      FROM [itsthe1.id].[checkinguest] g
--                     WHERE g.CheckinId = [itsthe1.id].[checkin].Id);

-- DELETE FROM [itsthe1.id].[payment]
--  WHERE NOT EXISTS (SELECT 1
--                      FROM [itsthe1.id].[checkin] c
--                     WHERE c.PaymentId = [itsthe1.id].[payment].Id);

-- -- Check the counts, then COMMIT or ROLLBACK.
-- ROLLBACK TRANSACTION;
-- -- COMMIT TRANSACTION;
GO
