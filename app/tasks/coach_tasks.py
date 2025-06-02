# app/tasks/coach_tasks.py
from celery import shared_task, chain, group
from app.services.coach_service import CoachService
from app.core.database import async_session
from celery import shared_task
import asyncio
import logging

from app.core.redis import redis_client  # فرض کنید redis_client دارید
import math
import json

logger = logging.getLogger(__name__)

@shared_task(bind=True, name="app.tasks.coach_tasks.update_coach_by_id_task")
def update_coach_by_id_task(self, coach_id: int):
    loop = asyncio.get_event_loop()
    if loop.is_closed():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    logger.info(f"Task started: update_coach_by_id_task with coach_id={coach_id}")
    try:
        result = loop.run_until_complete(_update_coach_by_id(coach_id))
        logger.info(f"Task completed successfully for coach ID={coach_id}.")
        return {
            "status": "success",
            "message": f"coach update task for ID={coach_id} completed successfully.",
            "details": result,  
            "task_id": self.request.id,
        }
    except Exception as e:
        logger.exception(f"Error in Celery task logic for coach ID={coach_id}: {e}")
        return {
            "status": "error",
            "message": f"Failed to update coach for ID={coach_id}: {str(e)}",
            "task_id": self.request.id,
        }

async def _update_coach_by_id(coach_id: int):
    session = await async_session()
    async with session as db:
        try:
            coach_service = CoachService()
            updated_coach = await coach_service.update_coach_by_id(db, coach_id)
            await session.commit()
            return {"coach_updated": updated_coach}
        except Exception as e:
            await session.rollback()
            logger.exception(f"Error in _update_coach_by_id for coach ID={coach_id}: {e}")
            raise
        finally:
            await session.close()



@shared_task(bind=True, name="app.tasks.coach_tasks.update_all_coaches_task")
async def update_all_coaches_task(self):
    logger.info("Starting update_all_coaches_task (manager task)")
    task_id = self.request.id
    num_chunks = 0 # مقدار اولیه
    group_id_val = None # مقدار اولیه

    try:
        total_coaches_count = 2529 # یا هر مقداری که دارید. مطمئن شوید این مقدار صحیح است.
        logger.info(f"[Task ID: {task_id}] Initializing Redis for coach update. Total coaches: {total_coaches_count}")

        async with redis_client.pipeline() as pipe:
            pipe.delete(f"coach_update:progress:{task_id}")
            pipe.delete(f"coach_update:errors:{task_id}")
            pipe.hset(f"coach_update:progress:{task_id}", "total", total_coaches_count)
            pipe.hset(f"coach_update:progress:{task_id}", "processed", 0)
            pipe.hset(f"coach_update:progress:{task_id}", "successful", 0)
            pipe.hset(f"coach_update:progress:{task_id}", "failed", 0)
            pipe.hset(f"coach_update:progress:{task_id}", "status", "processing") # وضعیت اولیه
            await pipe.execute()
        logger.info(f"[Task ID: {task_id}] Redis initialized successfully.")

        chunk_size = 100
        if total_coaches_count <= 0:
            logger.warning(f"[Task ID: {task_id}] Total coaches count is {total_coaches_count}. No chunks to process.")
            num_chunks = 0
            chunk_tasks = []
        else:
            num_chunks = math.ceil(total_coaches_count / chunk_size)
            logger.info(f"[Task ID: {task_id}] Calculated {num_chunks} chunks with chunk size {chunk_size}.")
            chunk_tasks = []
            for i in range(num_chunks):
                start = i * chunk_size + 1
                end = min((i + 1) * chunk_size, total_coaches_count)
                logger.debug(f"[Task ID: {task_id}] Creating task signature for chunk: start={start}, end={end}")
                # process_coach_chunk باید تسک دیگر شما باشد
                chunk_tasks.append(process_coach_chunk.s(start, end, task_id))

        if chunk_tasks:
            task_group = group(chunk_tasks)
            group_result_obj = task_group.apply_async() # این یک آبجکت همگام است
            group_id_val = group_result_obj.id
            logger.info(f"[Task ID: {task_id}] Dispatched {len(chunk_tasks)} chunk tasks. Group ID: {group_id_val}")
            await redis_client.hset(f"coach_update:progress:{task_id}", "group_id", group_id_val)
        else:
            logger.info(f"[Task ID: {task_id}] No chunk tasks were created to dispatch.")
            await redis_client.hset(f"coach_update:progress:{task_id}", "status", "completed_no_chunks")


        logger.info(f"[Task ID: {task_id}] update_all_coaches_task completed successfully dispatching chunks.")
        return {
            "status": "started",
            "message": "Coach update process chunks dispatched (or no chunks to dispatch).",
            "task_id": task_id,
            "chunks_created": num_chunks,
            "group_id": group_id_val
        }
    except Exception as e:
        # <<< لاگ دقیق استثنای اصلی >>>
        logger.error(f"!!! ORIGINAL EXCEPTION IN update_all_coaches_task (ID: {task_id}) !!!")
        logger.error(f"Exception type: {type(e).__name__}") # استفاده از __name__ برای جلوگیری از سریالایز نشدن خود type
        logger.error(f"Exception message: {str(e)}") # str(e) معمولا امن است
        formatted_traceback = traceback.format_exc()
        logger.error(f"Traceback: {formatted_traceback}")
        # <<< پایان لاگ دقیق >>>

        error_message_for_user = f"An error occurred in manager task: {str(e)}"
        exception_type_name = type(e).__name__

        # تلاش برای ذخیره خطا در Redis
        try:
            async with redis_client.pipeline() as pipe:
                pipe.hset(f"coach_update:progress:{task_id}", "status", "error_manager_task")
                pipe.hset(f"coach_update:progress:{task_id}", "error_message_manager", error_message_for_user)
                pipe.hset(f"coach_update:progress:{task_id}", "error_type_manager", exception_type_name)
                # ذخیره بخشی از traceback برای دیباگ (ممکن است طولانی باشد)
                pipe.hset(f"coach_update:progress:{task_id}", "error_traceback_manager_snippet", formatted_traceback[:1000])
                await pipe.execute()
            logger.info(f"[Task ID: {task_id}] Error details saved to Redis for manager task.")
        except Exception as redis_err:
            logger.error(f"[Task ID: {task_id}] Failed to update Redis on error for manager task: {type(redis_err).__name__} - {str(redis_err)}")

        # ساخت یک دیکشنری نتیجه که قطعاً قابل سریالایز شدن است
        # از برگرداندن خود آبجکت استثنا یا traceback کامل در نتیجه خودداری کنید
        # مگر اینکه مطمئن باشید سریالایزرهای Celery می‌توانند آن را مدیریت کنند.
        # Celery خودش سعی می‌کند استثنا را سریالایز کند اگر شما آن را raise کنید.
        # برای جلوگیری از خطای دوگانه سریالایزیشن، یک payload ساده برمی‌گردانیم.
        final_error_payload = {
            "status": "error",
            "message": error_message_for_user,
            "task_id": task_id,
            "exception_type": exception_type_name,
            "details": "Error occurred in the main task dispatching chunks. Check worker logs for full traceback."
        }

        # قبل از return، بررسی می‌کنیم که آیا خود این payload قابل سریالایز شدن است
        try:
            json.dumps(final_error_payload)
        except TypeError as te_json:
            logger.error(f"[Task ID: {task_id}] CRITICAL: Could not serialize final_error_payload: {str(te_json)}. Returning minimal error.")
            return {
                "status": "error",
                "message": "Critical error in manager task, and error details could not be serialized.",
                "task_id": task_id,
                "exception_type": "SerializationFailure" # یک نوع خطای سفارشی
            }
        
        # اگر نمی‌خواهید نتیجه‌ای برگردانید و اجازه دهید Celery خودش استثنا را مدیریت کند (که ممکن است منجر به خطای سریالایزیشن شود):
        # raise e # یا یک استثنای سفارشی و ساده‌تر: raise RuntimeError(error_message_for_user) from e

        return final_error_payload # برگرداندن دیکشنری ساده و قابل سریالایز
    
@shared_task(bind=True, name="app.tasks.coach_tasks.process_coach_chunk")
async def process_coach_chunk(self, start: int, end: int, parent_task_id: str): # <<< تغییر به async def
    logger.info(f"Processing coach chunk from {start} to {end} for parent task {parent_task_id}")
    processed_data = {} # برای نگهداری نتیجه پردازش
    try:
        # _process_coach_chunk یک کوروتین است، مستقیماً await می‌شود
        processed_data = await _process_coach_chunk(start, end)

        # به‌روزرسانی وضعیت در Redis به صورت ناهمگام
        async with redis_client.pipeline() as pipe:
            pipe.hincrby(f"coach_update:progress:{parent_task_id}", "processed", processed_data.get("processed", 0))
            pipe.hincrby(f"coach_update:progress:{parent_task_id}", "successful", processed_data.get("successful", 0))
            pipe.hincrby(f"coach_update:progress:{parent_task_id}", "failed", processed_data.get("failed", 0))

            for error_detail in processed_data.get("errors", []):
                error_str = json.dumps(error_detail) if not isinstance(error_detail, (str, bytes)) else error_detail
                pipe.rpush(f"coach_update:errors:{parent_task_id}", error_str)
            await pipe.execute() # <<< await

        return {
            "status": "success",
            "start": start,
            "end": end,
            "result": processed_data
        }
    except Exception as e:
        logger.exception(f"Error in process_coach_chunk for {start}-{end}: {e}")
        num_items_in_chunk = end - start + 1
        # در صورت خطا، وضعیت failed را نیز در Redis ثبت کنید
        async with redis_client.pipeline() as pipe:
            pipe.hincrby(f"coach_update:progress:{parent_task_id}", "processed", num_items_in_chunk) # همه پردازش شده (با خطا)
            pipe.hincrby(f"coach_update:progress:{parent_task_id}", "failed", num_items_in_chunk)
            error_info = {"range": f"{start}-{end}", "error": f"Chunk processing exception: {str(e)}"}
            pipe.rpush(f"coach_update:errors:{parent_task_id}", json.dumps(error_info))
            await pipe.execute() # <<< await

        return {
            "status": "error",
            "message": str(e),
            "start": start,
            "end": end
        }

# _process_coach_chunk همانطور که بود باقی می‌ماند (از قبل async است)
# فقط مطمئن شوید که تمام عملیات داخلی آن (مانند coach_service و db) نیز ناهمگام هستند.
async def _process_coach_chunk(start: int, end: int):
    """پردازش ناهمزمان یک بسته مربی‌ها"""
    logger.debug(f"Starting _process_coach_chunk for coaches {start}-{end}")
    # async_session باید یک context manager ناهمگام باشد
    async with async_session() as db: # اطمینان از اینکه async_session به درستی کار می‌کند
        try:
            coach_service = CoachService() # فرض بر اینکه CoachService برای کار با db ناهمگام طراحی شده
            coach_ids = list(range(start, end + 1)) # یا روش دقیق‌تر برای گرفتن ID ها
            if not coach_ids:
                 logger.warning(f"No coach IDs to process for range {start}-{end} in _process_coach_chunk")
                 return {"processed": 0, "successful": 0, "failed": 0, "errors": []}

            # coach_service.update_coaches_by_ids باید یک کوروتین باشد
            results = await coach_service.update_coaches_by_ids(db, coach_ids)
            # await db.commit() # اگر سرویس commit نمی‌کند، اینجا انجام دهید

            logger.info(f"Successfully processed chunk {start}-{end}. Successful: {results.get('successful',0)}, Failed: {results.get('failed',0)}")
            return {
                "processed": results.get("processed", len(coach_ids)), # اگر سرویس "processed" را برنگرداند
                "successful": results.get("successful", 0),
                "failed": results.get("failed", 0),
                "errors": results.get("errors", [])
            }
        except Exception as e:
            # await db.rollback() # اگر نیاز است
            logger.exception(f"Critical error in _process_coach_chunk for {start}-{end}: {e}")
            num_ids = len(coach_ids) if 'coach_ids' in locals() and coach_ids else (end - start + 1)
            return {
                "processed": num_ids,
                "successful": 0,
                "failed": num_ids,
                "errors": [{"id_range": f"{start}-{end}", "error": f"Chunk processing failed due to exception: {str(e)}"}]
            }