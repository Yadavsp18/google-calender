import json
import re

# ==========================================================
# LOAD DATA
# ==========================================================
def load_products(filename="products.json"):
    with open(filename, "r") as f:
        raw_data = json.load(f)
    
    products = []
    
    for product in raw_data:
        new_product = {"Product Name": product["Product Name"]}
        
        # Get ALL capacity values from all families
        capacities = []
        if product.get("Product Family 1 Maximum Capacity"):
            capacities.append(product.get("Product Family 1 Maximum Capacity"))
        if product.get("Product Family 2 Maximum Capacity"):
            capacities.append(product.get("Product Family 2 Maximum Capacity"))
        if product.get("Product Family 3 Maximum Capacity"):
            capacities.append(product.get("Product Family 3 Maximum Capacity"))
        
        # Get ALL floor values from all families
        floors = []
        if product.get("Product Family 1 Maximum floor (G+n)"):
            floors.append(product.get("Product Family 1 Maximum floor (G+n)"))
        if product.get("Product Family 1 Maximum floor (G+n).1"):
            floors.append(product.get("Product Family 1 Maximum floor (G+n).1"))
        if product.get("Product Family 2 Maximum floor (G+n)"):
            floors.append(product.get("Product Family 2 Maximum floor (G+n)"))
        if product.get("Product Family 3 Maximum floor (G+n)"):
            floors.append(product.get("Product Family 3 Maximum floor (G+n)"))
        
        # Use Key Feature 1 Max Value for speed if available (for Evora), else fall back to Tech Spec Speed Max
        speed_max_value = product.get("Key Feature 1 Max Value")
        if speed_max_value is None:
            speed_max_value = product.get("Tech Spec Speed Max")
        
        # Get Speed Min from Tech Spec Speed Min
        speed_min_value = product.get("Tech Spec Speed Min")
        
        # Get customization options
        customizations = []
        if product.get("Customization Availability 1"):
            customizations.append(product.get("Customization Availability 1"))
        if product.get("Customization Availability 2"):
            customizations.append(product.get("Customization Availability 2"))
        if product.get("Customization Availability 3"):
            customizations.append(product.get("Customization Availability 3"))
        
        # Get benefits
        benefits = []
        if product.get("Benefit 1"):
            benefits.append(product.get("Benefit 1"))
        if product.get("Benefit 2"):
            benefits.append(product.get("Benefit 2"))
        if product.get("Benefit 3"):
            benefits.append(product.get("Benefit 3"))
        if product.get("Benefit 4"):
            benefits.append(product.get("Benefit 4"))
        if product.get("Benefit 5"):
            benefits.append(product.get("Benefit 5"))
        
        feature_mappings = {
            "Capacity": product.get("Product Family 3 Maximum Capacity"),
            "Floor": product.get("Product Family 3 Maximum floor (G+n)"),
            "Duty Cycle": product.get("Duty Cycle value"),
            "Speed": speed_max_value,
            "Speed Min": speed_min_value,
            "Speed Max": speed_max_value,
            "Power": product.get("Tech Spec Power Max"),
            "Customization": ", ".join(filter(None, customizations)) if customizations else None,
            "Benefit": ", ".join(filter(None, benefits)) if benefits else None,
            # Add ALL capacity values for comprehensive checking
            "All Capacities": capacities,
            "Max Capacity": max(capacities) if capacities else None,
            # Add ALL floor values for comprehensive checking
            "All Floors": floors,
            "Max Floor": max(floors) if floors else None,
        }
        
        # Add mapped features
        for feature_name, value in feature_mappings.items():
            if value is not None:
                new_product[feature_name] = value
                # Extract numeric value
                num = extract_number_from_value(value)
                if num is not None:
                    new_product[feature_name + "_num"] = num
        
        # Also add raw keys from JSON
        for key, value in product.items():
            if key == "Product Name":
                continue
            if key not in new_product:
                new_product[key] = value
                # Extract numeric value if present
                num = extract_number_from_value(value)
                if num is not None:
                    new_product[key + "_num"] = num
        
        products.append(new_product)
    
    return products


# ==========================================================
# EXTRACT NUMERIC FROM VALUE
# ==========================================================
def extract_number_from_value(value):
    if value is None:
        return None
    
    numbers = re.findall(r"\d+\.?\d*", str(value))
    if numbers:
        return max(float(n) for n in numbers)
    
    return None


# ==========================================================
# INTENT DETECTION (Priority Based)
# ==========================================================
def detect_intent(question):
    q = question.lower()
    
    if "between" in q:
        return "between"
    
    if "at least" in q or ">=" in q or "minimum" in q:
        return "atleast"
    
    if "at most" in q or "<=" in q:
        return "atmost"
    
    if any(x in q for x in ["greater than", "more than", "above", "higher than"]):
        return "greater"
    
    if any(x in q for x in ["less than", "below", "under"]):
        return "less"
    
    if "top" in q:
        return "top"
    
    # Check for "maximum" and "max" separately from "at most"
    if any(x in q for x in ["maximum", "max", "highest"]):
        return "max"
    
    if any(x in q for x in ["minimum", "min", "lowest"]):
        return "min"
    
    return "text"


# ==========================================================
# FEATURE DETECTION (Improved)
# ==========================================================
def detect_feature(question, products):
    q = question.lower()
    
    # Feature detection patterns - order matters, check more specific first
    if "floor" in q or "floors" in q:
        return "Max Floor"
    
    if "duty cycle" in q or "duty cycle value" in q:
        return "Duty Cycle"
    
    if "speed max" in q or "maximum speed" in q or "fastest" in q:
        return "Speed Max"
    
    if "speed min" in q or "minimum speed" in q or "slowest" in q:
        return "Speed Min"
    
    if "speed" in q or "m/s" in q:
        return "Speed"
    
    if "power" in q or "kw" in q or "consume" in q:
        return "Power"
    
    if "capacity" in q or "kg" in q or "load" in q:
        return "Max Capacity"
    
    # Customization detection
    if "custom" in q or "option" in q or "variation" in q:
        return "Customization"
    
    # Benefit detection
    if "benefit" in q or "advantage" in q:
        return "Benefit"
    
    return None


# ==========================================================
# DETECT PRODUCT NAME
# ==========================================================
def detect_product_name(question, products):
    q = question.lower()
    
    for product in products:
        product_name = product.get("Product Name", "").lower()
        product_name_short = product_name.replace("eon ", "")
        
        if product_name in q or product_name_short in q:
            return product["Product Name"]
    
    return None


# ==========================================================
# EXTRACT NUMBERS FROM QUESTION
# ==========================================================
def extract_numbers(question):
    return [float(n) for n in re.findall(r"\d+\.?\d*", question)]


# ==========================================================
# GET PRODUCT BY NAME
# ==========================================================
def get_product_by_name(products, name):
    name_lower = name.lower()
    
    for product in products:
        product_name = product.get("Product Name", "").lower()
        product_name_short = product_name.replace("eon ", "")
        
        if name_lower == product_name or name_lower == product_name_short:
            return product
    
    return None


# ==========================================================
# GET FEATURE VALUE
# ==========================================================
def get_feature_value(product, feature):
    if feature in product:
        return product[feature]
    return None


# ==========================================================
# APPLY FILTER
# ==========================================================
def apply_filter(products, feature, intent, question):
    if not products:
        return []
    
    # Handle text-based features (like Customization and Benefit)
    if feature in ["Customization", "Benefit"]:
        if intent == "text" or intent is None:
            return products  # Return all products that have this feature
        return []
    
    # Find the numeric key
    numeric_key = feature + "_num"
    
    # Special case: use Max Capacity_num or Max Floor_num or Speed Min_num or Speed Max_num
    if feature in ["Max Capacity", "Max Floor", "Speed Min", "Speed Max"]:
        numeric_key = feature + "_num"
    
    if numeric_key not in products[0]:
        return []
    
    values = [p for p in products if numeric_key in p]
    
    numbers = [float(n) for n in re.findall(r"\d+\.?\d*", question)]
    
    if intent == "between" and len(numbers) >= 2:
        low, high = numbers[0], numbers[1]
        return [p for p in values if low <= p[numeric_key] <= high]
    
    if intent == "greater" and numbers:
        return [p for p in values if p[numeric_key] > numbers[0]]
    
    if intent == "less" and numbers:
        return [p for p in values if p[numeric_key] < numbers[0]]
    
    if intent == "atleast" and numbers:
        return [p for p in values if p[numeric_key] >= numbers[0]]
    
    if intent == "atmost" and numbers:
        return [p for p in values if p[numeric_key] <= numbers[0]]
    
    if intent == "max":
        return [max(values, key=lambda x: x[numeric_key])] if values else []
    
    if intent == "min":
        return [min(values, key=lambda x: x[numeric_key])] if values else []
    
    if intent == "top":
        n = int(numbers[0]) if numbers else 1
        sorted_products = sorted(values, key=lambda x: x[numeric_key], reverse=True)
        return sorted_products[:n]
    
    return []


# ==========================================================
# FORMAT FEATURE NAME
# ==========================================================
def format_feature_name(feature):
    feature_formats = {
        "Capacity": "maximum capacity",
        "Max Capacity": "maximum capacity",
        "Floor": "maximum floor supported",
        "Max Floor": "maximum floor supported",
        "Duty Cycle": "duty cycle value",
        "Speed": "maximum speed",
        "Speed Min": "minimum speed",
        "Speed Max": "maximum speed",
        "Power": "maximum power",
        "Customization": "customization options",
        "Benefit": "benefits"
    }
    return feature_formats.get(feature, feature)


# ==========================================================
# GET UNIT FOR FEATURE
# ==========================================================
def get_unit_for_feature(feature, products):
    units = {
        "Capacity": "kg",
        "Max Capacity": "kg",
        "Floor": "floors",
        "Max Floor": "floors",
        "Duty Cycle": "",
        "Speed": "m/s",
        "Speed Min": "m/s",
        "Speed Max": "m/s",
        "Power": "kW",
        "Customization": "",
        "Benefit": ""
    }
    unit = units.get(feature, "")
    return unit.strip()


# ==========================================================
# ANSWER ENGINE
# ==========================================================
def answer_question(question, products):
    q = question.lower()
    
    # Handle "Show details" / "Tell me about" / "Give me specs" type questions
    if any(x in q for x in ["show details", "tell me about", "give me specs", "give me complete", "give me the"]):
        product_name = detect_product_name(q, products)
        if product_name:
            product = get_product_by_name(products, product_name)
            if product:
                return format_product_details(product)
        return "Product not found."
    
    # Handle specific product feature queries
    product_name = detect_product_name(q, products)
    feature = detect_feature(question, products)
    
    # If we have a specific product and a feature, get the specific value
    if product_name and feature:
        product = get_product_by_name(products, product_name)
        if product:
            value = get_feature_value(product, feature)
            if value is not None:
                unit = get_unit_for_feature(feature, products)
                return f"{product['Product Name']} has {format_feature_name(feature)} of {value} {unit}.".strip()
    
    # Handle "highest/lowest" questions about a feature
    if any(x in q for x in ["highest", "lowest", "highest number", "lowest number"]):
        if feature:
            if "highest" in q:
                intent = "max"
            else:
                intent = "min"
            
            result = apply_filter(products, feature, intent, question)
            if result and len(result) == 1:
                p = result[0]
                value = get_feature_value(p, feature)
                unit = get_unit_for_feature(feature, products)
                return f"{p['Product Name']} has {format_feature_name(feature)} of {value} {unit}.".strip()
            elif result:
                return "Matching products: " + ", ".join(p["Product Name"] for p in result)
    
    # Handle "top N" questions - return exactly N products
    if "top" in q and feature:
        intent = "top"
        numbers = extract_numbers(question)
        n = int(numbers[0]) if numbers else 1
        
        # Get sorted products
        numeric_key = feature + "_num"
        if numeric_key in products[0]:
            sorted_products = sorted(products, key=lambda x: x.get(numeric_key, 0), reverse=True)
            # Handle ties - include all products that have the same value as the nth product
            if n < len(sorted_products):
                threshold_value = sorted_products[n-1].get(numeric_key, 0)
                # Include all products with value >= threshold
                result = [p for p in sorted_products if p.get(numeric_key, 0) >= threshold_value]
            else:
                result = sorted_products[:n]
            if result:
                unit = get_unit_for_feature(feature, products)
                return "Top products: " + ", ".join(
                    f"{p['Product Name']} ({get_feature_value(p, feature)} {unit})" for p in result
                )
    
    # Handle AND conditions FIRST - before single "between" check
    if " and " in q:
        filtered_products = products
        
        # Parse the question to find all conditions
        conditions = []
        nums = extract_numbers(q)
        
        # Track which numbers have been used
        used_nums = []
        
        def get_next_nums(count, used):
            """Get next 'count' numbers that haven't been used"""
            result = []
            for n in nums:
                if n not in used and len(result) < count:
                    result.append(n)
            return result
        
        # Check for duty cycle conditions FIRST (before capacity)
        if "duty cycle" in q or "duty" in q:
            if "between" in q and len(nums) >= 2:
                pair = get_next_nums(2, used_nums)
                if len(pair) >= 2:
                    conditions.append(("Duty Cycle", "between", pair[0], pair[1]))
                    used_nums.extend(pair)
            elif any(x in q for x in ["more than", "above"]) and nums:
                val = get_next_nums(1, used_nums)
                if val:
                    conditions.append(("Duty Cycle", "greater", val[0]))
                    used_nums.append(val[0])
            elif any(x in q for x in ["less than", "below"]) and nums:
                val = get_next_nums(1, used_nums)
                if val:
                    conditions.append(("Duty Cycle", "less", val[0]))
                    used_nums.append(val[0])
            elif any(x in q for x in ["at least"]) and nums:
                val = get_next_nums(1, used_nums)
                if val:
                    conditions.append(("Duty Cycle", "atleast", val[0]))
                    used_nums.append(val[0])
            elif any(x in q for x in ["at most"]) and nums:
                val = get_next_nums(1, used_nums)
                if val:
                    conditions.append(("Duty Cycle", "atmost", val[0]))
                    used_nums.append(val[0])
        
        # Check for speed conditions
        if "speed" in q or "m/s" in q:
            if "between" in q and len(nums) >= 2:
                pair = get_next_nums(2, used_nums)
                if len(pair) >= 2:
                    conditions.append(("Speed", "between", pair[0], pair[1]))
                    used_nums.extend(pair)
            elif any(x in q for x in ["more than", "above"]) and nums:
                val = get_next_nums(1, used_nums)
                if val:
                    conditions.append(("Speed", "greater", val[0]))
                    used_nums.append(val[0])
            elif any(x in q for x in ["less than", "below"]) and nums:
                val = get_next_nums(1, used_nums)
                if val:
                    conditions.append(("Speed", "less", val[0]))
                    used_nums.append(val[0])
            elif any(x in q for x in ["at least"]) and nums:
                val = get_next_nums(1, used_nums)
                if val:
                    conditions.append(("Speed", "atleast", val[0]))
                    used_nums.append(val[0])
            elif any(x in q for x in ["at most"]) and nums:
                val = get_next_nums(1, used_nums)
                if val:
                    conditions.append(("Speed", "atmost", val[0]))
                    used_nums.append(val[0])
        
        # Check for capacity conditions (after duty cycle)
        if "capacity" in q or "kg" in q:
            if "between" in q and len(nums) >= 2:
                pair = get_next_nums(2, used_nums)
                if len(pair) >= 2:
                    conditions.append(("Capacity", "between", pair[0], pair[1]))
                    used_nums.extend(pair)
            elif any(x in q for x in ["more than", "above", "greater than"]) and nums:
                val = get_next_nums(1, used_nums)
                if val:
                    conditions.append(("Capacity", "greater", val[0]))
                    used_nums.append(val[0])
            elif any(x in q for x in ["less than", "below", "under"]) and nums:
                val = get_next_nums(1, used_nums)
                if val:
                    conditions.append(("Capacity", "less", val[0]))
                    used_nums.append(val[0])
            elif any(x in q for x in ["at least", "minimum"]) and nums:
                val = get_next_nums(1, used_nums)
                if val:
                    conditions.append(("Capacity", "atleast", val[0]))
                    used_nums.append(val[0])
            elif any(x in q for x in ["at most", "maximum"]) and nums:
                val = get_next_nums(1, used_nums)
                if val:
                    conditions.append(("Capacity", "atmost", val[0]))
                    used_nums.append(val[0])
        
        # Check for floor conditions
        if "floor" in q:
            if "between" in q and len(nums) >= 2:
                pair = get_next_nums(2, used_nums)
                if len(pair) >= 2:
                    conditions.append(("Floor", "between", pair[0], pair[1]))
                    used_nums.extend(pair)
            elif any(x in q for x in ["more than", "above", "greater than"]) and nums:
                val = get_next_nums(1, used_nums)
                if val:
                    conditions.append(("Floor", "greater", val[0]))
                    used_nums.append(val[0])
            elif any(x in q for x in ["less than", "below", "under"]) and nums:
                val = get_next_nums(1, used_nums)
                if val:
                    conditions.append(("Floor", "less", val[0]))
                    used_nums.append(val[0])
            elif any(x in q for x in ["at least", "minimum"]) and nums:
                val = get_next_nums(1, used_nums)
                if val:
                    conditions.append(("Floor", "atleast", val[0]))
                    used_nums.append(val[0])
            elif any(x in q for x in ["at most", "maximum"]) and nums:
                val = get_next_nums(1, used_nums)
                if val:
                    conditions.append(("Floor", "atmost", val[0]))
                    used_nums.append(val[0])
        
        # Check for duty cycle conditions
        if "duty cycle" in q or "duty" in q:
            if "between" in q and len(nums) >= 2:
                pair = get_next_nums(2, used_nums)
                if len(pair) >= 2:
                    conditions.append(("Duty Cycle", "between", pair[0], pair[1]))
                    used_nums.extend(pair)
            elif any(x in q for x in ["more than", "above"]) and nums:
                val = get_next_nums(1, used_nums)
                if val:
                    conditions.append(("Duty Cycle", "greater", val[0]))
                    used_nums.append(val[0])
            elif any(x in q for x in ["less than", "below"]) and nums:
                val = get_next_nums(1, used_nums)
                if val:
                    conditions.append(("Duty Cycle", "less", val[0]))
                    used_nums.append(val[0])
            elif any(x in q for x in ["at least"]) and nums:
                val = get_next_nums(1, used_nums)
                if val:
                    conditions.append(("Duty Cycle", "atleast", val[0]))
                    used_nums.append(val[0])
            elif any(x in q for x in ["at most"]) and nums:
                val = get_next_nums(1, used_nums)
                if val:
                    conditions.append(("Duty Cycle", "atmost", val[0]))
                    used_nums.append(val[0])
        
        # Check for speed conditions
        if "speed" in q or "m/s" in q:
            if "between" in q and len(nums) >= 2:
                pair = get_next_nums(2, used_nums)
                if len(pair) >= 2:
                    conditions.append(("Speed", "between", pair[0], pair[1]))
                    used_nums.extend(pair)
            elif any(x in q for x in ["more than", "above"]) and nums:
                val = get_next_nums(1, used_nums)
                if val:
                    conditions.append(("Speed", "greater", val[0]))
                    used_nums.append(val[0])
            elif any(x in q for x in ["less than", "below"]) and nums:
                val = get_next_nums(1, used_nums)
                if val:
                    conditions.append(("Speed", "less", val[0]))
                    used_nums.append(val[0])
            elif any(x in q for x in ["at least"]) and nums:
                val = get_next_nums(1, used_nums)
                if val:
                    conditions.append(("Speed", "atleast", val[0]))
                    used_nums.append(val[0])
            elif any(x in q for x in ["at most"]) and nums:
                val = get_next_nums(1, used_nums)
                if val:
                    conditions.append(("Speed", "atmost", val[0]))
                    used_nums.append(val[0])
        
        # Check for power conditions
        if "power" in q or "kw" in q:
            if "between" in q and len(nums) >= 2:
                pair = get_next_nums(2, used_nums)
                if len(pair) >= 2:
                    conditions.append(("Power", "between", pair[0], pair[1]))
                    used_nums.extend(pair)
            elif any(x in q for x in ["more than", "above"]) and nums:
                val = get_next_nums(1, used_nums)
                if val:
                    conditions.append(("Power", "greater", val[0]))
                    used_nums.append(val[0])
            elif any(x in q for x in ["less than", "below"]) and nums:
                val = get_next_nums(1, used_nums)
                if val:
                    conditions.append(("Power", "less", val[0]))
                    used_nums.append(val[0])
            elif any(x in q for x in ["at least"]) and nums:
                val = get_next_nums(1, used_nums)
                if val:
                    conditions.append(("Power", "atleast", val[0]))
                    used_nums.append(val[0])
            elif any(x in q for x in ["at most"]) and nums:
                val = get_next_nums(1, used_nums)
                if val:
                    conditions.append(("Power", "atmost", val[0]))
                    used_nums.append(val[0])
        
        # Apply all conditions
        for feat, intent, *values in conditions:
            numeric_key = feat + "_num"
            if numeric_key not in products[0]:
                continue
            
            if intent == "between" and len(values) >= 2:
                low, high = values[0], values[1]
                filtered_products = [p for p in filtered_products if low <= p.get(numeric_key, 0) <= high]
            elif intent == "greater" and values:
                filtered_products = [p for p in filtered_products if p.get(numeric_key, 0) > values[0]]
            elif intent == "less" and values:
                filtered_products = [p for p in filtered_products if p.get(numeric_key, 0) < values[0]]
            elif intent == "atleast" and values:
                filtered_products = [p for p in filtered_products if p.get(numeric_key, 0) >= values[0]]
            elif intent == "atmost" and values:
                filtered_products = [p for p in filtered_products if p.get(numeric_key, 0) <= values[0]]
        
        if not filtered_products:
            return "No matching products found."
        
        return "Matching products: " + ", ".join(p["Product Name"] for p in filtered_products)
    
    # Handle single "between" questions (without "and")
    if " between " in q and feature:
        intent = "between"
        result = apply_filter(products, feature, intent, question)
        if not result:
            return "No matching products found."
        return "Matching products: " + ", ".join(p["Product Name"] for p in result)
    
    # Handle "more than" / "less than" / "at least" / "at most" questions
    if any(x in q for x in ["more than", "less than", "at least", "at most", "above", "below", "under"]):
        if feature:
            intent = detect_intent(question)
            result = apply_filter(products, feature, intent, question)
            if not result:
                return "No matching products found."
            return "Matching products: " + ", ".join(p["Product Name"] for p in result)
    
    # Single condition
    intent = detect_intent(question)
    if feature is None:
        feature = detect_feature(question, products)
    
    if not feature:
        return "Could not detect feature."
    
    # Handle Customization queries
    if feature == "Customization":
        # Check if a specific product is mentioned
        product_name = detect_product_name(question, products)
        if product_name:
            # Return customization for specific product
            for p in products:
                if p["Product Name"] == product_name:
                    cust = p.get("Customization", "")
                    if cust:
                        return f"{p['Product Name']} has the following customization options: {cust}"
                    return f"No customization information available for {product_name}."
        # Return customization options for all products
        result = []
        for p in products:
            cust = p.get("Customization", "")
            if cust:
                result.append(f"{p['Product Name']}: {cust}")
        if result:
            return "Customization options available:\n" + "\n".join(result)
        return "No customization information available."
    
    # Handle Benefit queries
    if feature == "Benefit":
        # Check if a specific product is mentioned
        product_name = detect_product_name(question, products)
        if product_name:
            # Return benefits for specific product
            for p in products:
                if p["Product Name"] == product_name:
                    benefit = p.get("Benefit", "")
                    if benefit:
                        return f"{p['Product Name']} has the following benefits: {benefit}"
                    return f"No benefit information available for {product_name}."
        # Return benefits for all products
        result = []
        for p in products:
            benefit = p.get("Benefit", "")
            if benefit:
                result.append(f"{p['Product Name']}: {benefit}")
        if result:
            return "Benefits available:\n" + "\n".join(result)
        return "No benefit information available."
    
    result = apply_filter(products, feature, intent, question)
    
    if not result:
        return "No matching products found."
    
    if intent in ["max", "min"]:
        p = result[0]
        value = get_feature_value(p, feature)
        unit = get_unit_for_feature(feature, products)
        return f"{p['Product Name']} has {format_feature_name(feature)} of {value} {unit}.".strip()
    
    if intent == "top":
        unit = get_unit_for_feature(feature, products)
        return "Top products: " + ", ".join(
            f"{p['Product Name']} ({get_feature_value(p, feature)} {unit})" for p in result
        )
    
    return "Matching products: " + ", ".join(p["Product Name"] for p in result)


# ==========================================================
# FORMAT PRODUCT DETAILS
# ==========================================================
def format_product_details(product):
    lines = []
    lines.append(f"=== {product.get('Product Name', 'Unknown')} ===")
    
    # Key specs
    if "Capacity" in product and product["Capacity"] is not None:
        lines.append(f"Maximum Capacity: {product['Capacity']} kg")
    if "Floor" in product and product["Floor"] is not None:
        lines.append(f"Maximum Floors: {product['Floor']}")
    if "Duty Cycle" in product and product["Duty Cycle"] is not None:
        lines.append(f"Duty Cycle: {product['Duty Cycle']}")
    if "Speed" in product and product["Speed"] is not None:
        lines.append(f"Maximum Speed: {product['Speed']} m/s")
    if "Power" in product and product["Power"] is not None:
        lines.append(f"Maximum Power: {product['Power']} kW")
    
    # Product Type
    if "Product Type" in product:
        lines.append(f"Product Type: {product['Product Type']}")
    
    # Application Range
    if "Application Range" in product:
        lines.append(f"Application Range: {product['Application Range']}")
    
    return "\n".join(lines)


# ==========================================================
# MAIN LOOP
# ==========================================================
if __name__ == "__main__":
    products = load_products()
    
    # Print available products
    print("Available products:", [p["Product Name"] for p in products])
    print("\n")
    
    while True:
        q = input("\nAsk your question (type 'exit' to quit): ")
        if q.lower() == "exit":
            break
        
        print(answer_question(q, products))
