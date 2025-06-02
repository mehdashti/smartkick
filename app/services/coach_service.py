# app/services/coach_service.py
from typing import List, Dict, Any, Optional, Tuple, Set
from itertools import islice
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, date
import logging
import math

from app.repositories.coach_repository import CoachRepository
from app.repositories.team_repository import TeamRepository

from app.services.team_service import TeamService

from app.api_clients import api_football
from app.core.config import settings
from app.models import Coach as DBCoach
from app.schemas.coach import (
    CoachCreateInternal,
    CoachApiResponse,
    CoachApiResponseItem,
    CoachBirthData,
)
from app.services.team_service import TeamService


logger = logging.getLogger(__name__)

class CoachService:

    def _parse_date(self, date_str: Optional[str]) -> Optional[date]:
        """Helper to parse date string, returning None if invalid."""
        if not date_str:
            return None
        try:
            return datetime.strptime(date_str, '%Y-%m-%d').date()
        except (ValueError, TypeError):
            logger.warning(f"Could not parse date string: '{date_str}'")
            return None

    async def _process_coach_api_data(
        self, db: AsyncSession,
        coach_raw_data: CoachApiResponseItem,
        team_ids_set: Set[int]
    ) -> Optional[Tuple[CoachCreateInternal, List[Dict[str, Any]], Set[int]]]:
        try:
            if not isinstance(coach_raw_data, CoachApiResponseItem):
                logger.error(f"Invalid input type for coach data: expected CoachApiResponseItem, got {type(coach_raw_data)}")
                return None

            team_service = TeamService()  
            team_repo = TeamRepository(db)

            career_data_json = [
                {
                    "id": career.team.id,
                    "name": career.team.name,
                    "logo": career.team.logo,
                    "start": career.start,
                    "end": career.end,
                }
                for career in coach_raw_data.career or []
                if career.team and career.team.id is not None
            ]

            for career_item in career_data_json:
                if not isinstance(career_item, dict) or 'id' not in career_item:
                    logger.error(f"Invalid career item format: {career_item}")
                    return None

            career_data_for_db: List[Dict[str, Any]] = []
            for career in coach_raw_data.career or []:
                if not career.team or not career.team.id:
                    continue

                if career.team.id not in team_ids_set:
                    logger.info(f"Team ID {career.team.id} not found locally. Attempting to fetch and update from API.")
                    try:
                        updated_team = await team_service.update_team_by_id(db, career.team.id)
                        if updated_team:
                            team_ids_set.add(career.team.id)
                        else:
                            team_data = {
                                "team_id": career.team.id,
                                "name": career.team.name,
                                "logo_url": career.team.logo,
                            }

                            updated_team = await team_repo.bulk_upsert_teams(team_data)
                        team_ids_set.add(career.team.id)
                    except Exception as e:
                        logger.error(f"Failed to update team ID {career.team.id}: {e}")
                        return None  # در صورت خطا، None برگردانید

                career_data_for_db.append({
                    "coach_id": coach_raw_data.id,
                    "team_id": career.team.id,
                    "team_name": career.team.name,
                    "logo_url": career.team.logo,
                    "start_date": self._parse_date(career.start) if career.start else None,
                    "end_date": self._parse_date(career.end) if career.end else None,
                })

            processed_data = CoachCreateInternal(
                id=coach_raw_data.id,
                name=coach_raw_data.name,
                firstname=coach_raw_data.firstname,
                lastname=coach_raw_data.lastname,
                age=coach_raw_data.age,
                birth_date=self._parse_date(coach_raw_data.birth.date) if coach_raw_data.birth else None,
                birth_place=coach_raw_data.birth.place if coach_raw_data.birth else None,
                birth_country=coach_raw_data.birth.country if coach_raw_data.birth else None,
                nationality=coach_raw_data.nationality,
                height=coach_raw_data.height,
                weight=coach_raw_data.weight,
                photo_url=coach_raw_data.photo,
                team_id=coach_raw_data.team.id if coach_raw_data.team else None,
                career=career_data_json,
            )

            if processed_data.id is None:
                logger.error(f"Processed coach data is missing id! Raw data: {coach_raw_data}")
                return None

            return processed_data, career_data_for_db, team_ids_set

        except Exception as e:
            logger.error(f"Failed to process coach data: {e}", exc_info=True)
            return None


    async def update_coach_by_id(
        self, db: AsyncSession, coach_id: int
    ) -> Optional[DBCoach]:
        logger.info(f"Starting single coach update process for ID: {coach_id}")
        coach_repo = CoachRepository(db)
        team_service = TeamService()  
        team_repo = TeamRepository(db)
        team_ids_set = set(await team_repo.get_all_teams_ids())    

        try:
            coach_api_data = await api_football.fetch_coach_by_id(coach_id)
            if not coach_api_data:
                logger.warning(f"No coach data found from API for ID: {coach_id}")
                return None
            
            result = CoachApiResponse(**coach_api_data)
            
            if not result.response or len(result.response) == 0:
                logger.warning(f"No coach data found in API response for ID: {coach_id}")
                return None
            
            processed_result = await self._process_coach_api_data(db, result.response[0], team_ids_set)
            if not processed_result:
                logger.error(f"Failed to process coach data from API for ID: {coach_id}")
                return None
            
            # باز کردن تاپل
            processed_data, career_data_for_db, team_ids_set = processed_result
            
            # ساخت لیست داده‌های مربی
            coach_data_list = [processed_data.model_dump()]
            upserted_coach = await coach_repo.bulk_upsert_coaches(coach_data_list)
            logger.info(f"Successfully upserted coach (ID: {coach_id})")

            # upsert داده‌های career
            if career_data_for_db:
                upserted_careers = await coach_repo.bulk_upsert_coaches_careers(career_data_for_db)
                logger.info(f"Successfully upserted {len(career_data_for_db)} coach careers for coach ID: {coach_id}")
            
            return upserted_coach

        except Exception as e:
            logger.exception(f"Database error during coach upsert for ID {coach_id}: {e}")
            raise


    async def update_all_coaches(self, db: AsyncSession) -> Dict[str, Any]:
        logger.info("Starting all coaches update process")

        coach_ids = range(1, 25300)
        batch_size = 100
        results = {"successful": 0, "failed": 0, "errors": []}

        coach_repo = CoachRepository(db)
        team_service = TeamService()
        team_repo = TeamRepository(db)
        team_ids_set = set(await team_repo.get_all_teams_ids())

        iterator = iter(coach_ids)
        while True:
            processed_coaches = []
            processed_careers = []
            unique_careers = {}  # برای اطمینان از یکتایی

            batch = list(islice(iterator, batch_size))
            if not batch:
                break

            logger.info(f"Processing batch of {len(batch)} coaches")

            for coach_id in batch:
                try:
                    coach_api_data = await api_football.fetch_coach_by_id(coach_id)
                    if not coach_api_data:
                        logger.warning(f"No coach data found from API for ID: {coach_id}")
                        results["failed"] += 1
                        results["errors"].append(f"No data for coach ID {coach_id}")
                        continue

                    raw_result = CoachApiResponse(**coach_api_data)
                    processed_result = await self._process_coach_api_data(db, raw_result.response[0], team_ids_set)
                    processed_data, career_data_for_db, team_ids_set = processed_result

                    processed_coaches.append(processed_data.model_dump())

                    if career_data_for_db:
                        for career in career_data_for_db:
                            # کلید یکتا برای هر سابقه کاری
                            key = (career["coach_id"], career["team_id"], career["start_date"])
                            unique_careers[key] = career  # فقط آخرین ردیف با این کلید نگه داشته می‌شود
                        results["successful"] += 1

                except Exception as e:
                    results["failed"] += 1
                    results["errors"].append(f"Coach ID {coach_id}: {str(e)}")
                    logger.error(f"Failed to update coach ID {coach_id}: {e}")

            # تبدیل دیکشنری به لیست برای upsert
            processed_careers = list(unique_careers.values())

            try:
                if processed_coaches:
                    upserted_coach = await coach_repo.bulk_upsert_coaches(processed_coaches)
                    logger.info(f"Successfully upserted {upserted_coach} coaches in batch")
                if processed_careers:
                    upserted_careers = await coach_repo.bulk_upsert_coaches_careers(processed_careers)
                    logger.info(f"Successfully upserted {upserted_careers} coach careers in batch")
                else:
                    logger.warning("No coach careers to upsert in batch")

            except Exception as e:
                results["failed"] += len(processed_coaches)
                results["errors"].append(f"Bulk upsert failed for batch: {str(e)}")
                logger.error(f"Bulk upsert failed for batch: {e}")

        return results
    

    async def update_coaches_by_ids(
        self, db: AsyncSession, coach_ids: List[int]
    ) -> Dict[str, Any]:
        """Update a batch of coaches by their IDs"""
        logger.info(f"Updating coaches batch: {len(coach_ids)} coaches")
        results = {"successful": 0, "failed": 0, "errors": []}
        
        # کش ID تیم‌ها برای کل بسته (یکبار در ابتدا)
        team_repo = TeamRepository(db)
        team_ids_set = set(await team_repo.get_all_teams_ids())
        
        processed_coaches = []
        processed_careers = []
        unique_careers = {}

        for coach_id in coach_ids:
            try:
                # دریافت داده‌ها از API
                coach_api_data = await api_football.fetch_coach_by_id(coach_id)
                if not coach_api_data:
                    raise ValueError(f"No data from API for coach ID {coach_id}")
                
                # پردازش داده‌ها
                raw_result = CoachApiResponse(**coach_api_data)
                if not raw_result.response:
                    raise ValueError(f"Empty response for coach ID {coach_id}")
                    
                processed_result = await self._process_coach_api_data(
                    db, 
                    raw_result.response[0], 
                    team_ids_set
                )
                
                if not processed_result:
                    raise ValueError(f"Processing failed for coach ID {coach_id}")
                
                processed_data, career_data_for_db, updated_team_ids = processed_result
                team_ids_set.update(updated_team_ids)  # به‌روزرسانی مجموعه ID تیم‌ها
                
                processed_coaches.append(processed_data.model_dump())
                
                # جمع‌آوری سوابق کاری
                if career_data_for_db:
                    for career in career_data_for_db:
                        key = (career["coach_id"], career["team_id"], career["start_date"])
                        unique_careers[key] = career
                        
                results["successful"] += 1
                
            except Exception as e:
                results["failed"] += 1
                error_msg = {
                    "coach_id": coach_id,
                    "error": str(e),
                    "timestamp": datetime.utcnow().isoformat()
                }
                results["errors"].append(error_msg)
                logger.error(f"Coach ID {coach_id}: {str(e)}")

        # ذخیره دسته‌ای در دیتابیس
        coach_repo = CoachRepository(db)
        try:
            if processed_coaches:
                await coach_repo.bulk_upsert_coaches(processed_coaches)
                logger.info(f"Upserted {len(processed_coaches)} coaches")
            
            if unique_careers:
                careers_list = list(unique_careers.values())
                await coach_repo.bulk_upsert_coaches_careers(careers_list)
                logger.info(f"Upserted {len(careers_list)} coach careers")
                
        except Exception as e:
            # فقط خطاهای دیتابیس را به عنوان شکست کلی در نظر نگیرید
            logger.exception(f"Bulk upsert failed: {e}")
            # می‌توانید خطاها را به results اضافه کنید اما بسته موفق در نظر گرفته می‌شود
            results["errors"].append({
                "type": "database",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            })

        return results