# etl_ingest.py
import json
from app.core.db import SessionLocal
from app.models import RawJSONFile, Patient, Visit, Encounter, Observation, IITFeatures
from datetime import datetime

def ingest_json_record(json_payload: dict):
        db = SessionLocal()
        try:
            msg = json_payload.get('messageData', {})
            demo = msg.get('demographics', {})
            patient_uuid = demo.get('patientUuid')  # may be None
            if not patient_uuid:
                # generate uuid or map from identifier
                patient_uuid = demo.get('patientUuid')  # fallback

            # save raw
            raw = RawJSONFile(patient_uuid=patient_uuid, facility_datim_code=json_payload.get('facilityDatimCode'), filename=json_payload.get('fileName'), raw_json=json_payload)
            db.add(raw)

            # upsert patient
            p = db.query(Patient).filter(Patient.patient_uuid == patient_uuid).one_or_none()
            if not p:
                p = Patient(patient_uuid=patient_uuid,
                            datim_id=demo.get('datimId'),
                            pepfar_id=None,
                            given_name=None,
                            family_name=None,
                            birthdate=demo.get('birthdate'),
                            gender=demo.get('gender'),
                            state=demo.get('stateProvince'),
                            city=demo.get('cityVillage'),
                            phone=demo.get('phoneNumber'))
                db.add(p)
            else:
                p.gender = demo.get('gender') or p.gender
                p.birthdate = demo.get('birthdate') or p.birthdate

            # visits
            for v in msg.get('visits', []):
                if v.get('voided', 0) == 1:
                    continue
                visit = Visit(patient_uuid=patient_uuid,
                              visit_type=v.get('visitType'),
                              date_started=v.get('dateStarted'),
                              date_stopped=v.get('dateStopped'),
                              voided=False)
                db.add(visit)

            # encounters
            for e in msg.get('encounters', []):
                if e.get('voided', 0) == 1:
                    continue
                encounter = Encounter(patient_uuid=patient_uuid,
                                      encounter_uuid=e.get('encounterUuid'),
                                      encounter_datetime=e.get('encounterDatetime'),
                                      encounter_type=e.get('encounterType'),
                                      pmm_form=e.get('pmmForm'),
                                      voided=False)
                db.add(encounter)

            # observations
            for o in msg.get('obs', []):
                if o.get('voided', 0) == 1:
                    continue
                obs = Observation(patient_uuid=patient_uuid,
                                  variable=o.get('variableName'),
                                  value_numeric=o.get('valueNumeric'),
                                  value_text=o.get('valueText'),
                                  value_coded=o.get('valueCoded'),
                                  obs_datetime=o.get('obsDatetime'),
                                  encounter_uuid=o.get('encounterUuid'),
                                  raw=o)
                db.add(obs)

            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()
