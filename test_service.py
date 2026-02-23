# services/test_service.py
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import logging
from bson import ObjectId

from database.models import Test, Question, TestSubmission, Application, Job
from database.repository import DatabaseRepository
from services.deepseek_service import deepseek_service

logger = logging.getLogger(__name__)

class TestService:
    """Service for managing tests, questions, and evaluations"""
    
    def __init__(self):
        self.db = DatabaseRepository()
    
    def create_test(self, job_id: str, title: str, description: str, 
                   duration_minutes: int = 60, passing_score: int = 70) -> str:
        """
        Create a new test for a job posting
        
        Args:
            job_id: ID of the job
            title: Test title
            description: Test description
            duration_minutes: Test duration in minutes
            passing_score: Minimum passing score percentage
            
        Returns:
            ID of the created test
        """
        try:
            test = Test(
                job_id=job_id,
                title=title,
                description=description,
                duration_minutes=duration_minutes,
                passing_score=passing_score,
                status="Draft"
            )
            
            test_id = self.db.insert_one("tests", test.to_dict())
            logger.info(f"Created test {test_id} for job {job_id}")
            return str(test_id)
            
        except Exception as e:
            logger.error(f"Error creating test: {str(e)}")
            raise
    
    def generate_questions_for_test(self, test_id: str, num_questions: int = 10) -> bool:
        """
        Generate questions for a test using DeepSeek API
        
        Args:
            test_id: ID of the test
            num_questions: Number of questions to generate
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Get test details
            test_data = self.db.find_one("tests", {"_id": ObjectId(test_id)})
            if not test_data:
                logger.error(f"Test {test_id} not found")
                return False
            
            test = Test.from_dict(test_data)
            
            # Get job details
            job_data = self.db.find_one("jobs", {"_id": ObjectId(test.job_id)})
            if not job_data:
                logger.error(f"Job {test.job_id} not found")
                return False
            
            job = Job.from_dict(job_data)
            
            # Generate questions using DeepSeek
            questions_data = deepseek_service.generate_test_questions(
                job.title, job.description, job.skills, job.experience, num_questions
            )
            
            if not questions_data:
                logger.error("Failed to generate questions")
                return False
            
            # Save questions to database
            for q_data in questions_data:
                question = Question(
                    test_id=test_id,
                    question_text=q_data["question_text"],
                    question_type="Multiple Choice",
                    options=q_data["options"],
                    correct_answer=q_data["correct_answer"],
                    points=q_data.get("points", 1),
                    difficulty=q_data.get("difficulty", "Medium"),
                    category=q_data.get("category", "General")
                )
                
                self.db.insert_one("questions", question.to_dict())
            
            # Update test status to Active
            self.db.update_one(
                "tests", 
                {"_id": ObjectId(test_id)}, 
                {"status": "Active", "scheduled_at": datetime.now()}
            )
            
            logger.info(f"Generated {len(questions_data)} questions for test {test_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error generating questions for test {test_id}: {str(e)}")
            return False
    
    def get_test_with_questions(self, test_id: str) -> Optional[Dict[str, Any]]:
        """
        Get test details along with its questions
        
        Args:
            test_id: ID of the test
            
        Returns:
            Test data with questions or None if not found
        """
        try:
            # Get test
            test_data = self.db.find_one("tests", {"_id": ObjectId(test_id)})
            if not test_data:
                return None
            
            # Get questions for this test
            questions_cursor = self.db.find_many("questions", {"test_id": test_id})
            questions = list(questions_cursor)
            
            # Convert ObjectIds to strings
            for question in questions:
                if "_id" in question:
                    question["_id"] = str(question["_id"])
            
            test_data["_id"] = str(test_data["_id"])
            test_data["questions"] = questions
            
            return test_data
            
        except Exception as e:
            logger.error(f"Error getting test {test_id}: {str(e)}")
            return None
    
    def start_test_submission(self, test_id: str, application_id: str, 
                            candidate_id: str) -> str:
        """
        Start a new test submission
        
        Args:
            test_id: ID of the test
            application_id: ID of the application
            candidate_id: ID of the candidate
            
        Returns:
            ID of the test submission
        """
        try:
            submission = TestSubmission(
                test_id=test_id,
                application_id=application_id,
                candidate_id=candidate_id,
                status="In Progress"
            )
            
            submission_id = self.db.insert_one("test_submissions", submission.to_dict())
            logger.info(f"Started test submission {submission_id} for candidate {candidate_id}")
            return str(submission_id)
            
        except Exception as e:
            logger.error(f"Error starting test submission: {str(e)}")
            raise
    
    def submit_test_answers(self, submission_id: str, answers: Dict[str, Any]) -> bool:
        """
        Submit answers for a test and automatically evaluate them
        
        Args:
            submission_id: ID of the test submission
            answers: Dictionary of question_id -> answer
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Get submission
            submission_data = self.db.find_one("test_submissions", {"_id": ObjectId(submission_id)})
            if not submission_data:
                logger.error(f"Submission {submission_id} not found")
                return False
            
            submission = TestSubmission.from_dict(submission_data)
            
            # Get test and questions
            test_data = self.db.find_one("tests", {"_id": ObjectId(submission.test_id)})
            if not test_data:
                logger.error(f"Test {submission.test_id} not found")
                return False
            
            questions_cursor = self.db.find_many("questions", {"test_id": submission.test_id})
            questions = list(questions_cursor)
            
            # Evaluate answers
            evaluation = self._evaluate_answers(questions, answers, test_data)
            
            # Update submission with results
            update_data = {
                "answers": answers,
                "score": evaluation["score"],
                "total_points": evaluation["total_points"],
                "percentage": evaluation["percentage"],
                "status": "Evaluated",
                "completed_at": datetime.now(),
                "evaluated_at": datetime.now()
            }
            
            self.db.update_one(
                "test_submissions",
                {"_id": ObjectId(submission_id)},
                update_data
            )
            
            # Update application status based on test result
            self._update_application_status(submission.application_id, evaluation)
            
            logger.info(f"Evaluated test submission {submission_id} with score {evaluation['percentage']:.1f}%")
            return True
            
        except Exception as e:
            logger.error(f"Error submitting test answers: {str(e)}")
            return False
    
    def _evaluate_answers(self, questions: List[Dict], answers: Dict[str, Any], 
                         test_data: Dict) -> Dict[str, Any]:
        """
        Evaluate test answers and calculate scores
        
        Args:
            questions: List of questions
            answers: Candidate's answers
            test_data: Test data for context
            
        Returns:
            Evaluation results
        """
        total_points = 0
        earned_points = 0
        question_evaluations = []
        
        for question in questions:
            question_id = str(question["_id"])
            correct_answer = question["correct_answer"]
            candidate_answer = answers.get(question_id, "")
            points = question.get("points", 1)
            
            total_points += points
            
            # Check if answer is correct
            is_correct = str(candidate_answer).strip().upper() == str(correct_answer).strip().upper()
            
            if is_correct:
                earned_points += points
            
            question_evaluations.append({
                "question_id": question_id,
                "correct": is_correct,
                "points_earned": points if is_correct else 0,
                "points_possible": points,
                "correct_answer": correct_answer,
                "candidate_answer": candidate_answer
            })
        
        percentage = (earned_points / total_points * 100) if total_points > 0 else 0
        passed = percentage >= test_data.get("passing_score", 70)
        
        return {
            "score": earned_points,
            "total_points": total_points,
            "percentage": percentage,
            "passed": passed,
            "question_evaluations": question_evaluations
        }
    
    def _update_application_status(self, application_id: str, evaluation: Dict[str, Any]):
        """Update application status based on test results"""
        try:
            if evaluation["passed"]:
                new_status = "Test Passed"
            else:
                new_status = "Test Failed"
            
            self.db.update_one(
                "applications",
                {"_id": ObjectId(application_id)},
                {"status": new_status, "updated_at": datetime.now()}
            )
            
        except Exception as e:
            logger.error(f"Error updating application status: {str(e)}")
    
    def get_test_results(self, submission_id: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed test results for a submission
        
        Args:
            submission_id: ID of the test submission
            
        Returns:
            Test results or None if not found
        """
        try:
            # Get submission
            submission_data = self.db.find_one("test_submissions", {"_id": ObjectId(submission_id)})
            if not submission_data:
                return None
            
            # Get test details
            test_data = self.db.find_one("tests", {"_id": ObjectId(submission_data["test_id"])})
            
            # Get questions with correct answers
            questions_cursor = self.db.find_many("questions", {"test_id": submission_data["test_id"]})
            questions = list(questions_cursor)
            
            # Format results
            results = {
                "submission": submission_data,
                "test": test_data,
                "questions": questions,
                "percentage": submission_data.get("percentage", 0),
                "passed": submission_data.get("percentage", 0) >= test_data.get("passing_score", 70)
            }
            
            # Convert ObjectIds to strings
            results["submission"]["_id"] = str(results["submission"]["_id"])
            results["test"]["_id"] = str(results["test"]["_id"])
            
            for question in results["questions"]:
                question["_id"] = str(question["_id"])
            
            return results
            
        except Exception as e:
            logger.error(f"Error getting test results: {str(e)}")
            return None
    
    def get_candidate_test_history(self, candidate_id: str) -> List[Dict[str, Any]]:
        """
        Get all test submissions for a candidate
        
        Args:
            candidate_id: ID of the candidate
            
        Returns:
            List of test submissions
        """
        try:
            submissions_cursor = self.db.find_many(
                "test_submissions", 
                {"candidate_id": candidate_id},
                sort=[("created_at", -1)]
            )
            
            submissions = []
            for submission in submissions_cursor:
                # Get test details
                test_data = self.db.find_one("tests", {"_id": ObjectId(submission["test_id"])})
                
                # Get application details
                application_data = self.db.find_one("applications", {"_id": ObjectId(submission["application_id"])})
                
                submission["_id"] = str(submission["_id"])
                submission["test"] = test_data
                submission["application"] = application_data
                
                submissions.append(submission)
            
            return submissions
            
        except Exception as e:
            logger.error(f"Error getting candidate test history: {str(e)}")
            return []
    
    def get_test_statistics(self, test_id: str) -> Dict[str, Any]:
        """
        Get statistics for a test
        
        Args:
            test_id: ID of the test
            
        Returns:
            Test statistics
        """
        try:
            # Get all submissions for this test
            submissions_cursor = self.db.find_many("test_submissions", {"test_id": test_id})
            submissions = list(submissions_cursor)
            
            if not submissions:
                return {
                    "total_submissions": 0,
                    "average_score": 0,
                    "pass_rate": 0,
                    "highest_score": 0,
                    "lowest_score": 0
                }
            
            total_submissions = len(submissions)
            scores = [s.get("percentage", 0) for s in submissions]
            passed_count = sum(1 for s in submissions if s.get("percentage", 0) >= 70)
            
            # Get test details for passing score
            test_data = self.db.find_one("tests", {"_id": ObjectId(test_id)})
            passing_score = test_data.get("passing_score", 70) if test_data else 70
            
            passed_count = sum(1 for s in submissions if s.get("percentage", 0) >= passing_score)
            
            statistics = {
                "total_submissions": total_submissions,
                "average_score": sum(scores) / total_submissions,
                "pass_rate": (passed_count / total_submissions * 100) if total_submissions > 0 else 0,
                "highest_score": max(scores),
                "lowest_score": min(scores),
                "passing_score": passing_score
            }
            
            return statistics
            
        except Exception as e:
            logger.error(f"Error getting test statistics: {str(e)}")
            return {}

# Singleton instance
test_service = TestService()